import os
import sqlite3

import matplotlib


matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

from database import DATABASE_FILENAME, close_connection, create_connection, refresh_database


plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False


HIGH_AMOUNT_THRESHOLD = 60.0


OVERVIEW_SQL = """
SELECT
    COUNT(*) AS record_count,
    COUNT(DISTINCT student_id) AS student_count,
    MIN(date) AS start_date,
    MAX(date) AS end_date,
    ROUND(SUM(amount), 2) AS total_amount,
    ROUND(AVG(amount), 2) AS average_amount
FROM consumption_records
"""


TOP_AMOUNT_STUDENTS_SQL = """
SELECT
    student_id,
    COUNT(*) AS transaction_count,
    ROUND(SUM(amount), 2) AS total_amount
FROM consumption_records
GROUP BY student_id
ORDER BY total_amount DESC, student_id ASC
LIMIT 10
"""


TOP_COUNT_STUDENTS_SQL = """
SELECT
    student_id,
    COUNT(*) AS transaction_count,
    ROUND(SUM(amount), 2) AS total_amount
FROM consumption_records
GROUP BY student_id
ORDER BY transaction_count DESC, total_amount DESC, student_id ASC
LIMIT 10
"""


CATEGORY_STATS_SQL = """
SELECT
    category,
    COUNT(*) AS transaction_count,
    ROUND(SUM(amount), 2) AS total_amount,
    ROUND(AVG(amount), 2) AS average_amount
FROM consumption_records
GROUP BY category
ORDER BY total_amount DESC, category ASC
"""


PAYMENT_STATS_SQL = """
SELECT
    payment_method,
    COUNT(*) AS usage_count,
    ROUND(SUM(amount), 2) AS total_amount
FROM consumption_records
GROUP BY payment_method
ORDER BY usage_count DESC, payment_method ASC
"""


MONTHLY_TREND_SQL = """
SELECT
    strftime('%Y-%m', date) AS month,
    COUNT(*) AS transaction_count,
    ROUND(SUM(amount), 2) AS total_amount
FROM consumption_records
GROUP BY strftime('%Y-%m', date)
ORDER BY month ASC
"""


DAILY_TREND_SQL = """
SELECT
    date,
    COUNT(*) AS transaction_count,
    ROUND(SUM(amount), 2) AS total_amount
FROM consumption_records
GROUP BY date
ORDER BY date ASC
"""


DAY_TYPE_SQL = """
SELECT
    date_type,
    COUNT(*) AS day_count,
    SUM(transaction_count) AS transaction_count,
    ROUND(SUM(total_amount), 2) AS total_amount,
    ROUND(SUM(total_amount) / SUM(transaction_count), 2) AS average_amount,
    ROUND(AVG(total_amount), 2) AS daily_average_amount
FROM (
    SELECT
        date,
        CASE
            WHEN strftime('%w', date) IN ('0', '6') THEN '周末'
            ELSE '工作日'
        END AS date_type,
        COUNT(*) AS transaction_count,
        SUM(amount) AS total_amount
    FROM consumption_records
    GROUP BY date
)
GROUP BY date_type
ORDER BY CASE date_type WHEN '工作日' THEN 1 ELSE 2 END
"""


HIGHEST_TRANSACTIONS_SQL = """
SELECT
    id,
    date,
    student_id,
    category,
    ROUND(amount, 2) AS amount,
    payment_method
FROM consumption_records
ORDER BY amount DESC, id ASC
LIMIT 10
"""


HIGH_AMOUNT_SUMMARY_SQL = """
SELECT
    COUNT(*) AS record_count,
    ROUND(SUM(amount), 2) AS total_amount,
    ROUND(AVG(amount), 2) AS average_amount
FROM consumption_records
WHERE amount >= ?
"""


def read_sql_results(connection, high_amount_threshold=HIGH_AMOUNT_THRESHOLD):
    """执行主要 SQL 查询，并将结果转换为 Pandas DataFrame。"""
    return {
        "overview": pd.read_sql_query(OVERVIEW_SQL, connection),
        "top_amount_students": pd.read_sql_query(
            TOP_AMOUNT_STUDENTS_SQL, connection
        ),
        "top_count_students": pd.read_sql_query(
            TOP_COUNT_STUDENTS_SQL, connection
        ),
        "category_stats": pd.read_sql_query(CATEGORY_STATS_SQL, connection),
        "payment_stats": pd.read_sql_query(PAYMENT_STATS_SQL, connection),
        "monthly_trend": pd.read_sql_query(MONTHLY_TREND_SQL, connection),
        "daily_trend": pd.read_sql_query(DAILY_TREND_SQL, connection),
        "day_type_stats": pd.read_sql_query(DAY_TYPE_SQL, connection),
        "highest_transactions": pd.read_sql_query(
            HIGHEST_TRANSACTIONS_SQL, connection
        ),
        "high_amount_summary": pd.read_sql_query(
            HIGH_AMOUNT_SUMMARY_SQL,
            connection,
            params=(high_amount_threshold,),
        ),
    }


def print_table(dataframe, column_names):
    """使用中文列名输出紧凑表格。"""
    display_data = dataframe.rename(columns=column_names)
    print(display_data.to_string(index=False))


def print_sql_results(results, high_amount_threshold=HIGH_AMOUNT_THRESHOLD):
    """将 SQL 查询结果清晰输出到控制台。"""
    overview = results["overview"].iloc[0]

    print("\n=================================")
    print("      SQLite / SQL 数据分析")
    print("=================================")

    print("\n【数据库基本信息】")
    print("记录数：{}".format(int(overview["record_count"])))
    print("学生数：{}".format(int(overview["student_count"])))
    print("日期范围：{} 至 {}".format(overview["start_date"], overview["end_date"]))
    print("总消费金额：{:.2f} 元".format(overview["total_amount"]))
    print("平均每笔消费：{:.2f} 元".format(overview["average_amount"]))

    print("\n【消费金额 Top 10 学生】")
    print_table(
        results["top_amount_students"],
        {
            "student_id": "学生ID",
            "transaction_count": "消费次数",
            "total_amount": "消费总金额",
        },
    )

    print("\n【消费次数 Top 10 学生】")
    print_table(
        results["top_count_students"],
        {
            "student_id": "学生ID",
            "transaction_count": "消费次数",
            "total_amount": "消费总金额",
        },
    )

    print("\n【各消费类型统计】")
    print_table(
        results["category_stats"],
        {
            "category": "消费类型",
            "transaction_count": "消费次数",
            "total_amount": "消费总金额",
            "average_amount": "平均消费金额",
        },
    )

    print("\n【支付方式统计】")
    print_table(
        results["payment_stats"],
        {
            "payment_method": "支付方式",
            "usage_count": "使用次数",
            "total_amount": "消费总金额",
        },
    )

    print("\n【月度消费趋势】")
    print_table(
        results["monthly_trend"],
        {
            "month": "月份",
            "transaction_count": "消费次数",
            "total_amount": "消费总金额",
        },
    )

    print("\n【工作日与周末对比】")
    print_table(
        results["day_type_stats"],
        {
            "date_type": "日期类型",
            "day_count": "天数",
            "transaction_count": "消费次数",
            "total_amount": "消费总金额",
            "average_amount": "平均每笔消费",
            "daily_average_amount": "日均消费金额",
        },
    )

    print("\n【单笔消费金额最高的 10 条记录】")
    print_table(
        results["highest_transactions"],
        {
            "id": "编号",
            "date": "日期",
            "student_id": "学生ID",
            "category": "消费类型",
            "amount": "消费金额",
            "payment_method": "支付方式",
        },
    )

    high_amount_summary = results["high_amount_summary"].iloc[0]
    print("\n【高额消费记录】")
    print("筛选条件：单笔消费金额 >= {:.2f} 元".format(high_amount_threshold))
    print("记录数：{}".format(int(high_amount_summary["record_count"])))
    print("消费总金额：{:.2f} 元".format(high_amount_summary["total_amount"]))
    print("平均消费金额：{:.2f} 元".format(high_amount_summary["average_amount"]))


def save_sql_charts(results, output_dir):
    """用 SQL 聚合结果生成两张图表。"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    top_students = results["top_amount_students"]
    student_positions = list(range(len(top_students)))
    student_values = top_students["total_amount"].values

    fig, ax = plt.subplots(figsize=(9, 6))
    bars = ax.barh(student_positions, student_values, color="#4C78A8")
    ax.set_title("SQL 查询：学生消费金额 Top 10")
    ax.set_xlabel("消费总金额（元）")
    ax.set_ylabel("学生 ID")
    ax.set_yticks(student_positions)
    ax.set_yticklabels(top_students["student_id"].tolist())
    ax.invert_yaxis()
    ax.set_xlim(0, max(student_values) * 1.18)
    for bar, amount in zip(bars, student_values):
        ax.text(
            bar.get_width(),
            bar.get_y() + bar.get_height() / 2,
            " {:.2f}".format(amount),
            ha="left",
            va="center",
            fontsize=8,
        )
    fig.tight_layout()
    fig.savefig(
        os.path.join(output_dir, "sql学生消费Top10.png"),
        dpi=150,
        bbox_inches="tight",
    )
    plt.close(fig)
    print("SQL 图表已生成：output/sql学生消费Top10.png")

    monthly_trend = results["monthly_trend"]
    month_positions = list(range(len(monthly_trend)))
    month_values = monthly_trend["total_amount"].values

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(
        month_positions,
        month_values,
        marker="o",
        linewidth=2,
        color="#F28E2B",
    )
    ax.set_title("SQL 查询：月度消费趋势")
    ax.set_xlabel("月份")
    ax.set_ylabel("消费总金额（元）")
    ax.set_xticks(month_positions)
    ax.set_xticklabels(monthly_trend["month"].tolist())
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    for position, amount in zip(month_positions, month_values):
        ax.text(
            position,
            amount,
            "{:.2f}".format(amount),
            ha="center",
            va="bottom",
            fontsize=8,
        )
    value_margin = max(month_values) * 0.08
    ax.set_ylim(min(month_values) - value_margin, max(month_values) + value_margin)
    fig.tight_layout()
    fig.savefig(
        os.path.join(output_dir, "sql月度消费趋势.png"),
        dpi=150,
        bbox_inches="tight",
    )
    plt.close(fig)
    print("SQL 图表已生成：output/sql月度消费趋势.png")


def generate_sql_report(
    results,
    report_path,
    high_amount_threshold=HIGH_AMOUNT_THRESHOLD,
):
    """根据 SQL 查询结果动态生成文字分析报告。"""
    overview = results["overview"].iloc[0]
    top_students = results["top_amount_students"]
    category_stats = results["category_stats"]
    payment_stats = results["payment_stats"]
    monthly_trend = results["monthly_trend"]
    day_type_stats = results["day_type_stats"]
    high_amount_summary = results["high_amount_summary"].iloc[0]

    top_category = category_stats.iloc[0]
    top_payment = payment_stats.iloc[0]
    top_month = monthly_trend.loc[monthly_trend["total_amount"].idxmax()]

    weekday = day_type_stats[day_type_stats["date_type"] == "工作日"].iloc[0]
    weekend = day_type_stats[day_type_stats["date_type"] == "周末"].iloc[0]
    daily_difference = abs(
        float(weekday["daily_average_amount"])
        - float(weekend["daily_average_amount"])
    )
    if weekday["daily_average_amount"] >= weekend["daily_average_amount"]:
        day_type_conclusion = "工作日日均消费比周末高 {:.2f} 元。".format(
            daily_difference
        )
    else:
        day_type_conclusion = "周末日均消费比工作日高 {:.2f} 元。".format(
            daily_difference
        )

    report_lines = [
        "校园消费 SQL 数据分析报告",
        "=" * 32,
        "",
        "一、数据库概况",
        "数据库表：consumption_records",
        "总记录数：{} 条".format(int(overview["record_count"])),
        "学生数量：{} 人".format(int(overview["student_count"])),
        "日期范围：{} 至 {}".format(
            overview["start_date"], overview["end_date"]
        ),
        "",
        "二、消费概况",
        "总消费金额：{:.2f} 元".format(overview["total_amount"]),
        "平均每笔消费金额：{:.2f} 元".format(overview["average_amount"]),
        "",
        "三、Top 10 消费学生",
    ]

    for rank, row in top_students.iterrows():
        report_lines.append(
            "  第{}名：{}，{} 次，{:.2f} 元".format(
                rank + 1,
                row["student_id"],
                int(row["transaction_count"]),
                row["total_amount"],
            )
        )

    report_lines.extend(["", "四、消费类型统计"])
    for unused_index, row in category_stats.iterrows():
        report_lines.append(
            "  {}：{} 次，总金额 {:.2f} 元，平均 {:.2f} 元".format(
                row["category"],
                int(row["transaction_count"]),
                row["total_amount"],
                row["average_amount"],
            )
        )

    report_lines.extend(["", "五、支付方式统计"])
    for unused_index, row in payment_stats.iterrows():
        report_lines.append(
            "  {}：{} 次，总金额 {:.2f} 元".format(
                row["payment_method"],
                int(row["usage_count"]),
                row["total_amount"],
            )
        )

    report_lines.extend(["", "六、月度消费趋势"])
    for unused_index, row in monthly_trend.iterrows():
        report_lines.append(
            "  {}：{} 次，总金额 {:.2f} 元".format(
                row["month"],
                int(row["transaction_count"]),
                row["total_amount"],
            )
        )

    report_lines.extend(["", "七、工作日与周末对比"])
    for unused_index, row in day_type_stats.iterrows():
        report_lines.append(
            "  {}：{} 天，{} 次，总金额 {:.2f} 元，笔均 {:.2f} 元，日均 {:.2f} 元".format(
                row["date_type"],
                int(row["day_count"]),
                int(row["transaction_count"]),
                row["total_amount"],
                row["average_amount"],
                row["daily_average_amount"],
            )
        )

    report_lines.extend([
        "",
        "八、WHERE 条件查询",
        "单笔消费金额不低于 {:.2f} 元的记录共有 {} 条，总金额 {:.2f} 元，平均 {:.2f} 元。".format(
            high_amount_threshold,
            int(high_amount_summary["record_count"]),
            high_amount_summary["total_amount"],
            high_amount_summary["average_amount"],
        ),
        "",
        "九、分析结论",
        "消费金额最高的类型是{}，总金额 {:.2f} 元。".format(
            top_category["category"], top_category["total_amount"]
        ),
        "使用次数最多的支付方式是{}，共使用 {} 次。".format(
            top_payment["payment_method"], int(top_payment["usage_count"])
        ),
        "消费金额最高的月份是{}，总金额 {:.2f} 元。".format(
            top_month["month"], top_month["total_amount"]
        ),
        day_type_conclusion,
        "本报告由 SQLite 查询结果自动生成，统计数字未手工写入。",
    ])

    with open(report_path, "w", encoding="utf-8") as report_file:
        report_file.write("\n".join(report_lines))

    print("SQL 分析报告已生成：sql_analysis_report.txt")


def run_sql_analysis(
    database_path,
    output_dir,
    report_path,
    high_amount_threshold=HIGH_AMOUNT_THRESHOLD,
):
    """执行 SQL 查询、控制台展示、绘图和报告生成。"""
    connection = None
    try:
        connection = create_connection(database_path)
        results = read_sql_results(connection, high_amount_threshold)
        print_sql_results(results, high_amount_threshold)
        save_sql_charts(results, output_dir)
        generate_sql_report(results, report_path, high_amount_threshold)
        return results
    except sqlite3.Error as error:
        print("SQLite / SQL 分析失败：{}".format(error))
        raise
    finally:
        close_connection(connection)


def main():
    project_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(project_dir, "data.csv")
    database_path = os.path.join(project_dir, DATABASE_FILENAME)
    output_dir = os.path.join(project_dir, "output")
    report_path = os.path.join(project_dir, "sql_analysis_report.txt")

    refresh_database(csv_path, database_path)
    run_sql_analysis(database_path, output_dir, report_path)


if __name__ == "__main__":
    main()
