import matplotlib.pyplot as plt
import pandas as pd
import pulp
import seaborn as sns
import streamlit as st
from ShiftScheduler import ShiftScheduler

calendar_df = None
staff_df = None

# タイトル
st.title("シフトスケジューリングアプリ")

# サイドバー
st.sidebar.header("データのアップロード")

calendar_file = "data/calendar.csv"
staff_file = "data/staff.csv"

# calendar_file = st.sidebar.file_uploader("カレンダー", type=["csv"])
# staff_file = st.sidebar.file_uploader("スタッフ情報", type=["csv"])

if calendar_file is not None:
    calendar_df = pd.read_csv(calendar_file)

if staff_file is not None:
    staff_df = pd.read_csv(staff_file)

# タブ
tab1, tab2, tab3 = st.tabs(["カレンダー情報", "スタッフ情報", "シフト表作成"])

with tab1:
    st.markdown("## カレンダー情報")
    if calendar_file is not None:
        st.write(calendar_df)

with tab2:
    st.markdown("## スタッフ情報")
    if staff_file is not None:
        st.write(staff_df)

with tab3:
    if calendar_file is None:
        st.markdown("#### カレンダーファイルをアップロードしてください")

    if staff_file is None:
        st.markdown("#### スタッフファイルをアップロードしてください")

    if calendar_file is not None and staff_file is not None:
        weight_list = []
        ng_list = []
        for staff_id in staff_df["スタッフID"]:
            weight = st.slider(f"{staff_id}の優先度", 0.0, 1.0, 0.5)
            weight_list.append(weight)
        weight_df = pd.DataFrame(
            {"スタッフID": staff_df["スタッフID"], "重要度": weight_list}
        )

        for staff_id in staff_df["スタッフID"]:
            ng_day = st.multiselect(f"{staff_id}の休暇希望日", calendar_df["日付"])
            ng_list.append(ng_day)

        all_combinations = [
            (staff_id, day)
            for staff_id in staff_df["スタッフID"]
            for day in calendar_df["日付"]
        ]

        # Create a DataFrame with all combinations
        ng_df = pd.DataFrame(all_combinations, columns=["スタッフID", "日付"])

        # Mark the days off in the DataFrame
        ng_df["休暇希望"] = ng_df.apply(
            lambda row: (
                0
                if row["日付"]
                in ng_list[staff_df["スタッフID"].tolist().index(row["スタッフID"])]
                else 1
            ),
            axis=1,
        )

        if st.button("最適化実行"):
            shift_sch = ShiftScheduler()
            shift_sch.set_data(staff_df, calendar_df, weight_df, ng_df)
            # shift_sch.show()
            shift_sch.build_model()
            shift_sch.solve()

            st.markdown("## 最適化結果")
            st.write("Status:", pulp.LpStatus[shift_sch.status])
            st.write("Objective:", shift_sch.model.objective.value())

            st.markdown("## シフト表")
            st.write(shift_sch.sch_df)

            st.markdown("## シフト数の充足確認")
            shift_df = shift_sch.sch_df
            sum_staff_df = shift_df.T.sum().reset_index()
            sum_staff_df.columns = ["Staff", "Count"]

            fig, ax = plt.subplots(figsize=(10, 6))
            sns.barplot(x="Staff", y="Count", data=sum_staff_df, ax=ax)
            st.pyplot(fig)

            st.markdown("## スタッフの希望の確認")
            st.markdown("## 責任者の合計シフト数の充足確認")
            merged_shift_df = pd.merge(
                shift_df,
                staff_df[["スタッフID", "責任者フラグ"]],
                left_index=True,
                right_on="スタッフID",
            )

            sum_day_nonres_df = (
                merged_shift_df[merged_shift_df["責任者フラグ"] == 0]
                .drop(columns=["スタッフID", "責任者フラグ"])
                .sum()
                .reset_index()
            )
            sum_day_nonres_df.columns = ["Day", "非責任者"]
            sum_day_res_df = (
                merged_shift_df[merged_shift_df["責任者フラグ"] == 1]
                .drop(columns=["スタッフID", "責任者フラグ"])
                .sum()
                .reset_index()
            )
            sum_day_res_df.columns = ["Day", "責任者"]

            sum_day_df = pd.merge(sum_day_nonres_df, sum_day_res_df, on="Day")
            sum_day_df = sum_day_df.set_index("Day")

            # 積み重ね棒グラフの作成
            fig, ax = plt.subplots(figsize=(10, 6))
            sum_day_df.plot(kind="bar", stacked=True, figsize=(10, 6), ax=ax)
            # グラフの装飾
            # plt.title("Stacked Bar Plot of Non-Residential and Residential Counts")
            plt.xlabel("Days")
            plt.ylabel("Counts")
            plt.legend(title="Position")
            plt.xticks(rotation=0)

            plt.tight_layout()
            st.pyplot(fig)

            st.download_button(
                label="Download CSV",
                data=shift_sch.sch_df.to_csv().encode("utf-8"),
                file_name="shift_schedule.csv",
                mime="text/csv",
            )
