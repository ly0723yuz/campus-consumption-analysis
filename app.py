import os
import sqlite3

import matplotlib


matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from database import DATABASE_FILENAME, close_connection, create_connection
from sql_analysis import read_sql_results


plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False


PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(PROJECT_DIR, "data.csv")
DATABASE_PATH = os.path.join(PROJECT_DIR, DATABASE_FILENAME)
CSV_COLUMNS = ["日期", "学生ID", "消费类型", "消费金额", "支付方式"]
PAGE_OPTIONS = [
    "数据总览",
    "消费趋势",
    "学生消费分析",
    "消费类型分析",
    "支付方式分析",
    "工作日 / 周末分析",
    "SQL 分析结果",
    "原始数据预览",
]


def load_csv_data(csv_path):
    """读取并进行适合看板展示的基础数据检查。"""
    data = pd.read_csv(csv_path, encoding="utf-8-sig")
    missing_columns = [column for column in CSV_COLUMNS if column not in data.columns]
    if missing_columns:
        raise ValueError("data.csv 缺少字段：{}".format("、".join(missing_columns)))

    data = data[CSV_COLUMNS].copy()
    data["日期"] = pd.to_datetime(data["日期"], errors="coerce")
    data["消费金额"] = pd.to_numeric(data["消费金额"], errors="coerce")
    data = data.dropna(subset=CSV_COLUMNS)
    data = data.drop_duplicates()
    data = data[data["消费金额"] > 0]
    data = data.sort_values("日期").reset_index(drop=True)

    if data.empty:
        raise ValueError("data.csv 中没有可用于看板分析的有效记录。")
    return data


def normalize_date_range(selected_dates, minimum_date, maximum_date):
    """兼容旧版 Streamlit 可能返回的单日期或日期序列。"""
    if isinstance(selected_dates, (list, tuple)):
        if len(selected_dates) >= 2:
            start_date = selected_dates[0]
            end_date = selected_dates[1]
        elif len(selected_dates) == 1:
            start_date = selected_dates[0]
            end_date = selected_dates[0]
        else:
            start_date = minimum_date
            end_date = maximum_date
    else:
        start_date = selected_dates
        end_date = selected_dates

    start_date = pd.Timestamp(start_date).normalize()
    end_date = pd.Timestamp(end_date).normalize()
    if start_date > end_date:
        start_date, end_date = end_date, start_date
    return start_date, end_date


def filter_consumption_data(
    data,
    start_date,
    end_date,
    selected_categories,
    selected_payment_methods,
):
    """按照日期、消费类型和支付方式组合筛选数据。"""
    if not selected_categories or not selected_payment_methods:
        return data.iloc[0:0].copy()

    start_timestamp = pd.Timestamp(start_date).normalize()
    end_timestamp = pd.Timestamp(end_date).normalize()
    if start_timestamp > end_timestamp:
        start_timestamp, end_timestamp = end_timestamp, start_timestamp

    condition = (
        (data["日期"] >= start_timestamp)
        & (data["日期"] <= end_timestamp)
        & data["消费类型"].isin(selected_categories)
        & data["支付方式"].isin(selected_payment_methods)
    )
    return data.loc[condition].copy()


def calculate_overview(data):
    """计算随筛选条件变化的核心指标。"""
    if data.empty:
        return {
            "record_count": 0,
            "student_count": 0,
            "total_amount": 0.0,
            "average_amount": 0.0,
            "per_student_amount": 0.0,
            "date_range": "无数据",
        }

    total_amount = float(data["消费金额"].sum())
    student_count = int(data["学生ID"].nunique())
    return {
        "record_count": int(len(data)),
        "student_count": student_count,
        "total_amount": round(total_amount, 2),
        "average_amount": round(float(data["消费金额"].mean()), 2),
        "per_student_amount": round(total_amount / student_count, 2),
        "date_range": "{} 至 {}".format(
            data["日期"].min().strftime("%Y-%m-%d"),
            data["日期"].max().strftime("%Y-%m-%d"),
        ),
    }


def calculate_daily_trend(data):
    """按日期汇总消费金额。"""
    trend = data.groupby("日期")["消费金额"].sum().sort_index().reset_index()
    trend.columns = ["日期", "消费总金额"]
    trend["消费总金额"] = trend["消费总金额"].round(2)
    return trend


def calculate_monthly_trend(data):
    """按月份汇总消费金额。"""
    monthly_data = data.copy()
    monthly_data["月份"] = monthly_data["日期"].dt.strftime("%Y-%m")
    trend = monthly_data.groupby("月份")["消费金额"].sum().sort_index().reset_index()
    trend.columns = ["月份", "消费总金额"]
    trend["消费总金额"] = trend["消费总金额"].round(2)
    return trend


def calculate_top_students(data, limit=10):
    """计算筛选范围内消费金额最高的学生。"""
    ranking = data.groupby("学生ID")["消费金额"].sum().reset_index()
    ranking.columns = ["学生ID", "消费总金额"]
    ranking = ranking.sort_values(
        ["消费总金额", "学生ID"], ascending=[False, True]
    ).head(limit)
    ranking["消费总金额"] = ranking["消费总金额"].round(2)
    return ranking.reset_index(drop=True)


def calculate_category_stats(data):
    """计算各消费类型的金额、次数和平均金额。"""
    grouped = data.groupby("消费类型")["消费金额"]
    stats = pd.DataFrame(
        {
            "消费总金额": grouped.sum(),
            "消费次数": grouped.count(),
            "平均消费金额": grouped.mean(),
        }
    ).reset_index()
    stats["消费总金额"] = stats["消费总金额"].round(2)
    stats["平均消费金额"] = stats["平均消费金额"].round(2)
    return stats.sort_values("消费总金额", ascending=False).reset_index(drop=True)


def calculate_payment_stats(data):
    """计算各支付方式的使用次数和消费金额。"""
    grouped = data.groupby("支付方式")["消费金额"]
    stats = pd.DataFrame(
        {
            "使用次数": grouped.count(),
            "消费总金额": grouped.sum(),
        }
    ).reset_index()
    stats["消费总金额"] = stats["消费总金额"].round(2)
    return stats.sort_values("使用次数", ascending=False).reset_index(drop=True)


def calculate_day_type_stats(data):
    """比较工作日和周末的消费金额及次数。"""
    day_type_data = data.copy()
    day_type_data["日期类型"] = day_type_data["日期"].dt.weekday.apply(
        lambda weekday: "工作日" if weekday < 5 else "周末"
    )
    grouped = day_type_data.groupby("日期类型")["消费金额"]
    amount_series = grouped.sum().reindex(["工作日", "周末"], fill_value=0)
    count_series = grouped.count().reindex(["工作日", "周末"], fill_value=0)
    stats = pd.DataFrame(
        {
            "日期类型": ["工作日", "周末"],
            "消费总金额": amount_series.values,
            "消费次数": count_series.values,
        }
    )
    stats["消费总金额"] = stats["消费总金额"].round(2)
    return stats


def get_data_preview(data, limit=50):
    """返回用于网页展示的有限条数数据。"""
    preview = data.head(limit).copy()
    if not preview.empty:
        preview["日期"] = preview["日期"].dt.strftime("%Y-%m-%d")
    return preview


def read_database_analysis(database_path):
    """只读现有 SQLite 数据库，并复用第五轮 SQL 查询函数。"""
    if not os.path.exists(database_path):
        raise FileNotFoundError("未找到 campus_consumption.db")

    connection = None
    try:
        connection = create_connection(database_path)
        table_row = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
            ("consumption_records",),
        ).fetchone()
        if table_row is None:
            raise ValueError("数据库中不存在 consumption_records 表。")
        return read_sql_results(connection)
    finally:
        close_connection(connection)


def display_figure(figure):
    """在 Streamlit 中显示 Matplotlib 图表并及时释放资源。"""
    st.pyplot(figure)
    plt.close(figure)


def render_overview(data):
    overview = calculate_overview(data)
    st.subheader("数据总览")

    first_row = st.columns(3)
    first_row[0].metric("总消费金额", "{:.2f} 元".format(overview["total_amount"]))
    first_row[1].metric("消费记录数", "{} 条".format(overview["record_count"]))
    first_row[2].metric("学生人数", "{} 人".format(overview["student_count"]))

    second_row = st.columns(3)
    second_row[0].metric(
        "平均每笔消费", "{:.2f} 元".format(overview["average_amount"])
    )
    second_row[1].metric(
        "人均累计消费", "{:.2f} 元".format(overview["per_student_amount"])
    )
    second_row[2].metric("日期范围", overview["date_range"])


def render_trends(data):
    st.header("消费趋势")
    daily_trend = calculate_daily_trend(data)
    monthly_trend = calculate_monthly_trend(data)

    st.subheader("每日消费金额趋势")
    positions = list(range(len(daily_trend)))
    labels = daily_trend["日期"].dt.strftime("%Y-%m-%d").tolist()
    figure, axis = plt.subplots(figsize=(10, 4.5))
    axis.plot(positions, daily_trend["消费总金额"].values, color="#4C78A8")
    axis.set_xlabel("日期")
    axis.set_ylabel("消费总金额（元）")
    axis.grid(axis="y", linestyle="--", alpha=0.35)
    tick_step = max(1, (len(labels) + 9) // 10)
    tick_positions = positions[::tick_step]
    axis.set_xticks(tick_positions)
    axis.set_xticklabels(labels[::tick_step], rotation=40, ha="right")
    figure.tight_layout()
    display_figure(figure)

    st.subheader("月度消费金额趋势")
    positions = list(range(len(monthly_trend)))
    figure, axis = plt.subplots(figsize=(9, 4.2))
    axis.plot(
        positions,
        monthly_trend["消费总金额"].values,
        marker="o",
        linewidth=2,
        color="#F28E2B",
    )
    axis.set_xlabel("月份")
    axis.set_ylabel("消费总金额（元）")
    axis.set_xticks(positions)
    axis.set_xticklabels(monthly_trend["月份"].tolist())
    axis.grid(axis="y", linestyle="--", alpha=0.35)
    figure.tight_layout()
    display_figure(figure)


def render_student_analysis(data):
    st.header("学生消费分析")
    st.caption("排行榜会根据当前筛选条件重新计算，最多展示 Top 10。")
    ranking = calculate_top_students(data)

    chart_column, table_column = st.columns(2)
    with chart_column:
        positions = list(range(len(ranking)))
        figure, axis = plt.subplots(figsize=(7, 5))
        axis.barh(positions, ranking["消费总金额"].values, color="#4C78A8")
        axis.set_xlabel("消费总金额（元）")
        axis.set_ylabel("学生 ID")
        axis.set_yticks(positions)
        axis.set_yticklabels(ranking["学生ID"].tolist())
        axis.invert_yaxis()
        figure.tight_layout()
        display_figure(figure)

    with table_column:
        st.dataframe(ranking, use_container_width=True)


def render_category_analysis(data):
    st.header("消费类型分析")
    stats = calculate_category_stats(data)

    positions = list(range(len(stats)))
    figure, axis = plt.subplots(figsize=(9, 4.8))
    axis.bar(positions, stats["消费总金额"].values, color="#76B7B2")
    axis.set_xlabel("消费类型")
    axis.set_ylabel("消费总金额（元）")
    axis.set_xticks(positions)
    axis.set_xticklabels(stats["消费类型"].tolist(), rotation=25, ha="right")
    figure.tight_layout()
    display_figure(figure)
    st.dataframe(stats, use_container_width=True)


def render_payment_analysis(data):
    st.header("支付方式分析")
    stats = calculate_payment_stats(data)
    positions = list(range(len(stats)))

    figure, axes = plt.subplots(1, 2, figsize=(10, 4.3))
    axes[0].bar(positions, stats["使用次数"].values, color="#59A14F")
    axes[0].set_title("支付方式使用次数")
    axes[0].set_ylabel("次数")
    axes[0].set_xticks(positions)
    axes[0].set_xticklabels(stats["支付方式"].tolist(), rotation=20)
    axes[1].bar(positions, stats["消费总金额"].values, color="#E15759")
    axes[1].set_title("支付方式消费金额")
    axes[1].set_ylabel("金额（元）")
    axes[1].set_xticks(positions)
    axes[1].set_xticklabels(stats["支付方式"].tolist(), rotation=20)
    figure.tight_layout()
    display_figure(figure)
    st.dataframe(stats, use_container_width=True)


def render_day_type_analysis(data):
    st.header("工作日 / 周末分析")
    stats = calculate_day_type_stats(data)
    positions = [0, 1]

    figure, axes = plt.subplots(1, 2, figsize=(9, 4.2))
    axes[0].bar(positions, stats["消费总金额"].values, color=["#4C78A8", "#F28E2B"])
    axes[0].set_title("消费总金额对比")
    axes[0].set_ylabel("金额（元）")
    axes[0].set_xticks(positions)
    axes[0].set_xticklabels(stats["日期类型"].tolist())
    axes[1].bar(positions, stats["消费次数"].values, color=["#4C78A8", "#F28E2B"])
    axes[1].set_title("消费次数对比")
    axes[1].set_ylabel("次数")
    axes[1].set_xticks(positions)
    axes[1].set_xticklabels(stats["日期类型"].tolist())
    figure.tight_layout()
    display_figure(figure)
    st.dataframe(stats, use_container_width=True)


def render_sql_analysis(database_path):
    st.header("SQL 分析结果")
    st.info(
        "本区域直接读取 campus_consumption.db，并复用 sql_analysis.py 的 SQL 查询函数。"
        "这里展示数据库全量统计，不受左侧 CSV 筛选条件影响。"
    )

    try:
        results = read_database_analysis(database_path)
    except FileNotFoundError:
        st.error("未找到 campus_consumption.db，请先运行 python main.py 初始化数据库。")
        return
    except (sqlite3.Error, ValueError) as error:
        st.error("读取 SQLite 数据失败：{}".format(error))
        return

    overview = results["overview"].iloc[0]
    sql_metrics = st.columns(3)
    sql_metrics[0].metric("数据库记录数", "{} 条".format(int(overview["record_count"])))
    sql_metrics[1].metric("数据库学生数", "{} 人".format(int(overview["student_count"])))
    sql_metrics[2].metric("SQL 总消费金额", "{:.2f} 元".format(overview["total_amount"]))

    st.subheader("SQL 查询：消费金额 Top 10 学生")
    top_students = results["top_amount_students"]
    positions = list(range(len(top_students)))
    figure, axis = plt.subplots(figsize=(8, 5))
    axis.barh(positions, top_students["total_amount"].values, color="#4C78A8")
    axis.set_xlabel("消费总金额（元）")
    axis.set_ylabel("学生 ID")
    axis.set_yticks(positions)
    axis.set_yticklabels(top_students["student_id"].tolist())
    axis.invert_yaxis()
    figure.tight_layout()
    display_figure(figure)
    st.dataframe(
        top_students.rename(
            columns={
                "student_id": "学生ID",
                "transaction_count": "消费次数",
                "total_amount": "消费总金额",
            }
        ),
        use_container_width=True,
    )

    st.subheader("SQL 查询：月度消费趋势")
    monthly_trend = results["monthly_trend"]
    positions = list(range(len(monthly_trend)))
    figure, axis = plt.subplots(figsize=(9, 4.2))
    axis.plot(
        positions,
        monthly_trend["total_amount"].values,
        marker="o",
        linewidth=2,
        color="#F28E2B",
    )
    axis.set_xlabel("月份")
    axis.set_ylabel("消费总金额（元）")
    axis.set_xticks(positions)
    axis.set_xticklabels(monthly_trend["month"].tolist())
    axis.grid(axis="y", linestyle="--", alpha=0.35)
    figure.tight_layout()
    display_figure(figure)
    st.dataframe(
        monthly_trend.rename(
            columns={
                "month": "月份",
                "transaction_count": "消费次数",
                "total_amount": "消费总金额",
            }
        ),
        use_container_width=True,
    )

    st.subheader("SQL 查询：各消费类型汇总")
    st.dataframe(
        results["category_stats"].rename(
            columns={
                "category": "消费类型",
                "transaction_count": "消费次数",
                "total_amount": "消费总金额",
                "average_amount": "平均消费金额",
            }
        ),
        use_container_width=True,
    )


def render_data_preview(data):
    st.header("原始数据预览")
    st.write("当前筛选结果共 {} 条，下面最多展示前 50 条。".format(len(data)))
    st.dataframe(get_data_preview(data, 50), use_container_width=True)


def render_selected_page(page_name, filtered_data, database_path):
    """根据侧边栏导航显示一个主要分析区域，避免页面过长。"""
    if page_name == "数据总览":
        st.write("请选择左侧筛选条件，页面指标会自动更新。")
    elif page_name == "消费趋势":
        render_trends(filtered_data)
    elif page_name == "学生消费分析":
        render_student_analysis(filtered_data)
    elif page_name == "消费类型分析":
        render_category_analysis(filtered_data)
    elif page_name == "支付方式分析":
        render_payment_analysis(filtered_data)
    elif page_name == "工作日 / 周末分析":
        render_day_type_analysis(filtered_data)
    elif page_name == "SQL 分析结果":
        render_sql_analysis(database_path)
    elif page_name == "原始数据预览":
        render_data_preview(filtered_data)


def main():
    st.set_page_config(page_title="校园消费数据分析系统", layout="wide")
    st.title("校园消费数据分析系统")
    st.markdown(
        "基于 Python + Pandas + SQLite + SQL + Streamlit 的校园消费数据分析项目"
    )

    if not os.path.exists(CSV_PATH):
        st.error("未找到 data.csv，请先运行 python generate_data.py。")
        return

    try:
        data = load_csv_data(CSV_PATH)
    except (IOError, ValueError) as error:
        st.error("读取校园消费数据失败：{}".format(error))
        return

    minimum_date = data["日期"].min().date()
    maximum_date = data["日期"].max().date()
    category_options = sorted(data["消费类型"].unique().tolist())
    payment_options = sorted(data["支付方式"].unique().tolist())

    st.sidebar.header("看板导航与筛选")
    selected_page = st.sidebar.radio("页面导航", PAGE_OPTIONS)
    selected_dates = st.sidebar.date_input(
        "日期范围",
        value=(minimum_date, maximum_date),
        min_value=minimum_date,
        max_value=maximum_date,
    )
    selected_categories = st.sidebar.multiselect(
        "消费类型", category_options, default=category_options
    )
    selected_payment_methods = st.sidebar.multiselect(
        "支付方式", payment_options, default=payment_options
    )

    start_date, end_date = normalize_date_range(
        selected_dates, minimum_date, maximum_date
    )
    filtered_data = filter_consumption_data(
        data,
        start_date,
        end_date,
        selected_categories,
        selected_payment_methods,
    )

    st.sidebar.markdown(
        "当前筛选：{} 至 {}，共 {} 条记录。".format(
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d"),
            len(filtered_data),
        )
    )

    render_overview(filtered_data)

    if filtered_data.empty:
        st.warning("当前筛选条件下没有数据，请调整日期、消费类型或支付方式。")
        if selected_page == "SQL 分析结果":
            render_sql_analysis(DATABASE_PATH)
        elif selected_page == "原始数据预览":
            render_data_preview(filtered_data)
        return

    render_selected_page(selected_page, filtered_data, DATABASE_PATH)


if __name__ == "__main__":
    main()
