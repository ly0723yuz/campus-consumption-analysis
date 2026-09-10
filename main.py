import os

import matplotlib


# 使用无界面后端，便于在服务器或命令行环境中稳定保存图表。
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd


plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False


print("================================")
print("      校园消费数据分析系统")
print("================================")

project_dir = os.path.dirname(os.path.abspath(__file__))
data_path = os.path.join(project_dir, "data.csv")
output_dir = os.path.join(project_dir, "output")
report_path = os.path.join(project_dir, "analysis_report.txt")
os.makedirs(output_dir, exist_ok=True)


def output_path(filename):
    return os.path.join(output_dir, filename)


def save_chart(fig, filename):
    path = output_path(filename)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("图表已生成：output/{}".format(filename))


# ==============================
# 数据读取、检查和清洗
# ==============================

data = pd.read_csv(data_path)
required_columns = ["日期", "学生ID", "消费类型", "消费金额", "支付方式"]
missing_columns = [column for column in required_columns if column not in data.columns]

if missing_columns:
    raise ValueError("数据缺少必要字段：" + "、".join(missing_columns))

raw_record_count = len(data)
missing_value_count = int(data[required_columns].isnull().sum().sum())
duplicate_count = int(data.duplicated().sum())

original_amount = data["消费金额"]
converted_amount = pd.to_numeric(original_amount, errors="coerce")
invalid_amount_count = int((original_amount.notnull() & converted_amount.isnull()).sum())
data["消费金额"] = converted_amount

original_date = data["日期"]
converted_date = pd.to_datetime(original_date, errors="coerce")
invalid_date_count = int((original_date.notnull() & converted_date.isnull()).sum())
data["日期"] = converted_date

abnormal_amount_count = int((data["消费金额"] <= 0).sum())

data = data.drop_duplicates().copy()
data = data.dropna(subset=required_columns)
data = data[data["消费金额"] > 0].copy()
data = data.sort_values(["日期", "学生ID"]).reset_index(drop=True)
removed_count = raw_record_count - len(data)

print("\n【数据清洗】")
print("原始记录数：", raw_record_count)
print("缺失值数量：", missing_value_count)
print("重复记录数量：", duplicate_count)
print("无法转换的消费金额：", invalid_amount_count)
print("异常消费记录（金额 <= 0）：", abnormal_amount_count)
print("日期格式异常记录：", invalid_date_count)
print("本次清洗删除记录：", removed_count)
print("数据清洗完成")

if data.empty:
    raise ValueError("清洗后没有可用于分析的数据。")

print("\n【数据预览（前 10 条）】")
print(data.head(10).to_string(index=False))


# ==============================
# 基础统计
# ==============================

count = len(data)
student_number = int(data["学生ID"].nunique())
active_day_count = int(data["日期"].nunique())
start_date = data["日期"].min().strftime("%Y-%m-%d")
end_date = data["日期"].max().strftime("%Y-%m-%d")

total_amount = float(data["消费金额"].sum())
average_amount = float(data["消费金额"].mean())
median_amount = float(data["消费金额"].median())
max_amount = float(data["消费金额"].max())
min_amount = float(data["消费金额"].min())
daily_average_amount = total_amount / active_day_count
per_student_average = total_amount / student_number

print("\n【基本统计】")
print("消费记录数：", count)
print("学生数量：", student_number)
print("活跃天数：", active_day_count)
print("日期范围：{} 至 {}".format(start_date, end_date))
print("总消费金额：{:.2f} 元".format(total_amount))
print("平均每笔消费：{:.2f} 元".format(average_amount))
print("消费金额中位数：{:.2f} 元".format(median_amount))
print("日均消费金额：{:.2f} 元".format(daily_average_amount))
print("人均累计消费：{:.2f} 元".format(per_student_average))
print("单笔最高消费金额：{:.2f} 元".format(max_amount))
print("单笔最低消费金额：{:.2f} 元".format(min_amount))


# ==============================
# 学生消费统计（只展示 Top 10）
# ==============================

student_total = data.groupby("学生ID")["消费金额"].sum()
student_count = data.groupby("学生ID").size()
student_ranking = student_total.sort_values(ascending=False)
student_top10 = student_ranking.head(10)
top_student = student_top10.index[0]
top_amount = float(student_top10.iloc[0])
top10_amount = float(student_top10.sum())
top10_ratio = top10_amount / total_amount * 100

most_frequent_count = int(student_count.max())
most_frequent_students = student_count[student_count == most_frequent_count].index.tolist()

print("\n【学生消费金额排行榜 Top 10】")
for rank, (student_id, amount) in enumerate(student_top10.iteritems(), start=1):
    print("第{}名：{}，消费金额：{:.2f} 元".format(rank, student_id, amount))

print("\n【消费次数最多的学生】")
print("学生ID：", "、".join(most_frequent_students))
print("消费次数：", most_frequent_count)
print("Top 10 学生消费占比：{:.1f}%".format(top10_ratio))


# ==============================
# 消费类型和支付方式统计
# ==============================

type_total = data.groupby("消费类型")["消费金额"].sum().sort_values(ascending=False)
type_count = data.groupby("消费类型").size().reindex(type_total.index)
type_average = data.groupby("消费类型")["消费金额"].mean().reindex(type_total.index)
top_type = type_total.index[0]
top_type_amount = float(type_total.iloc[0])
top_type_ratio = top_type_amount / total_amount * 100

print("\n【消费类型统计】")
for consumption_type in type_total.index:
    print("{}：{} 次，{:.2f} 元，笔均 {:.2f} 元".format(
        consumption_type,
        int(type_count[consumption_type]),
        type_total[consumption_type],
        type_average[consumption_type],
    ))

payment_total = data.groupby("支付方式")["消费金额"].sum()
payment_count = data.groupby("支付方式").size()
payment_count_ranking = payment_count.sort_values(ascending=False)
max_payment_count = int(payment_count_ranking.iloc[0])
most_used_payments = payment_count[payment_count == max_payment_count].index.tolist()

print("\n【支付方式统计】")
for payment_method in payment_count_ranking.index:
    print("{}：{} 次，{:.2f} 元".format(
        payment_method,
        int(payment_count[payment_method]),
        payment_total[payment_method],
    ))


# ==============================
# 时间趋势与工作日/周末对比
# ==============================

daily_total = data.groupby("日期")["消费金额"].sum().sort_index()
daily_count = data.groupby("日期").size().sort_index()
peak_date = daily_total.idxmax()
peak_date_amount = float(daily_total.max())
peak_count_date = daily_count.idxmax()
peak_date_count = int(daily_count.max())

data["日期类型"] = data["日期"].dt.dayofweek.map(
    lambda value: "工作日" if value < 5 else "周末"
)
day_type_order = ["工作日", "周末"]
day_type_total = data.groupby("日期类型")["消费金额"].sum().reindex(day_type_order)
day_type_count = data.groupby("日期类型").size().reindex(day_type_order)
day_type_average = data.groupby("日期类型")["消费金额"].mean().reindex(day_type_order)

calendar_days = data[["日期", "日期类型"]].drop_duplicates()
day_type_days = calendar_days.groupby("日期类型").size().reindex(day_type_order)
day_type_daily_average = day_type_total / day_type_days
weekend_amount_ratio = float(day_type_total["周末"] / total_amount * 100)

data["月份"] = data["日期"].dt.strftime("%Y-%m")
monthly_total = data.groupby("月份")["消费金额"].sum().sort_index()
monthly_count = data.groupby("月份").size().reindex(monthly_total.index)

weekday_names = {
    0: "周一",
    1: "周二",
    2: "周三",
    3: "周四",
    4: "周五",
    5: "周六",
    6: "周日",
}
data["星期序号"] = data["日期"].dt.dayofweek
weekday_total = data.groupby("星期序号")["消费金额"].sum().reindex(range(7), fill_value=0)

print("\n【工作日与周末消费对比】")
for day_type in day_type_order:
    print("{}：{} 天，{} 笔，总金额 {:.2f} 元，笔均 {:.2f} 元，日均 {:.2f} 元".format(
        day_type,
        int(day_type_days[day_type]),
        int(day_type_count[day_type]),
        day_type_total[day_type],
        day_type_average[day_type],
        day_type_daily_average[day_type],
    ))
print("周末消费金额占比：{:.1f}%".format(weekend_amount_ratio))

print("\n【月度消费趋势】")
for month in monthly_total.index:
    print("{}：{} 笔，{:.2f} 元".format(
        month,
        int(monthly_count[month]),
        monthly_total[month],
    ))


# ==============================
# 自动生成文字分析报告
# ==============================

top_daily_totals = daily_total.sort_values(ascending=False).head(5)
report_lines = [
    "校园消费数据分析报告",
    "=" * 30,
    "",
    "一、数据基本情况",
    "数据记录数：{} 条".format(count),
    "学生数量：{} 人".format(student_number),
    "活跃天数：{} 天".format(active_day_count),
    "数据日期范围：{} 至 {}".format(start_date, end_date),
    "数据清洗删除记录：{} 条".format(removed_count),
    "",
    "二、整体消费情况",
    "总消费金额：{:.2f} 元".format(total_amount),
    "平均每笔消费：{:.2f} 元".format(average_amount),
    "消费金额中位数：{:.2f} 元".format(median_amount),
    "日均消费金额：{:.2f} 元".format(daily_average_amount),
    "人均累计消费：{:.2f} 元".format(per_student_average),
    "单笔最高消费：{:.2f} 元".format(max_amount),
    "单笔最低消费：{:.2f} 元".format(min_amount),
    "",
    "三、学生消费情况",
    "消费金额最高的学生：{}（{:.2f} 元）".format(top_student, top_amount),
    "消费次数最多的学生：{}（{} 次）".format(
        "、".join(most_frequent_students), most_frequent_count
    ),
    "Top 10 学生累计消费：{:.2f} 元，占总消费的 {:.1f}%".format(
        top10_amount, top10_ratio
    ),
    "学生消费排行榜 Top 10：",
]

for rank, (student_id, amount) in enumerate(student_top10.iteritems(), start=1):
    report_lines.append("  第{}名：{}，{:.2f} 元".format(rank, student_id, amount))

report_lines.extend([
    "",
    "四、消费类型分析",
    "各消费类型金额、次数和笔均金额：",
])

for consumption_type in type_total.index:
    report_lines.append("  {}：{} 次，{:.2f} 元，笔均 {:.2f} 元".format(
        consumption_type,
        int(type_count[consumption_type]),
        type_total[consumption_type],
        type_average[consumption_type],
    ))

report_lines.extend([
    "消费金额最高的类型：{}，{:.2f} 元，占总消费的 {:.1f}%".format(
        top_type, top_type_amount, top_type_ratio
    ),
    "",
    "五、支付方式分析",
    "各支付方式使用次数和消费金额：",
])

for payment_method in payment_count_ranking.index:
    report_lines.append("  {}：{} 次，{:.2f} 元".format(
        payment_method,
        int(payment_count[payment_method]),
        payment_total[payment_method],
    ))

report_lines.extend([
    "使用次数最多的支付方式：{}（{} 次）".format(
        "、".join(most_used_payments), max_payment_count
    ),
    "",
    "六、工作日与周末消费对比",
])

for day_type in day_type_order:
    report_lines.append("  {}：{} 天，{} 笔，总金额 {:.2f} 元，笔均 {:.2f} 元，日均 {:.2f} 元".format(
        day_type,
        int(day_type_days[day_type]),
        int(day_type_count[day_type]),
        day_type_total[day_type],
        day_type_average[day_type],
        day_type_daily_average[day_type],
    ))

report_lines.extend([
    "周末消费金额占比：{:.1f}%".format(weekend_amount_ratio),
    "",
    "七、月度与每日趋势",
    "各月消费金额：",
])

for month in monthly_total.index:
    report_lines.append("  {}：{} 笔，{:.2f} 元".format(
        month, int(monthly_count[month]), monthly_total[month]
    ))

report_lines.append("消费金额最高的 5 个日期：")
for date, amount in top_daily_totals.iteritems():
    report_lines.append("  {}：{:.2f} 元".format(date.strftime("%Y-%m-%d"), amount))

report_lines.extend([
    "消费金额最高的一天：{}，{:.2f} 元".format(
        peak_date.strftime("%Y-%m-%d"), peak_date_amount
    ),
    "消费笔数最多的一天：{}，{} 笔".format(
        peak_count_date.strftime("%Y-%m-%d"), peak_date_count
    ),
    "",
    "八、分析总结",
    "样本覆盖 {} 名学生和 {} 个活跃日，共形成 {} 条有效消费记录。".format(
        student_number, active_day_count, count
    ),
    "消费金额主要集中在{}，金额为 {:.2f} 元，占总消费的 {:.1f}%。".format(
        top_type, top_type_amount, top_type_ratio
    ),
    "工作日日均消费 {:.2f} 元，周末日均消费 {:.2f} 元；周末消费金额占比为 {:.1f}%。".format(
        day_type_daily_average["工作日"],
        day_type_daily_average["周末"],
        weekend_amount_ratio,
    ),
    "学生消费排行榜仅展示 Top 10，避免大样本下输出过长。",
    "本报告基于固定随机种子生成的模拟数据，仅用于项目演示和分析练习。",
])

with open(report_path, "w", encoding="utf-8") as report_file:
    report_file.write("\n".join(report_lines))

print("\n分析报告已生成：analysis_report.txt")


# ==============================
# 图表：全部保存到 output/
# ==============================

fig, ax = plt.subplots(figsize=(9, 5))
type_total.plot(kind="bar", ax=ax, color="#4C78A8")
ax.set_title("校园消费类型统计")
ax.set_xlabel("消费类型")
ax.set_ylabel("消费金额（元）")
ax.tick_params(axis="x", rotation=25)
save_chart(fig, "消费类型统计.png")

date_labels = [date.strftime("%Y-%m-%d") for date in daily_total.index]
x_positions = list(range(len(date_labels)))
fig, ax = plt.subplots(figsize=(11, 5))
ax.plot(x_positions, daily_total.values, color="#4C78A8", linewidth=1.5)
ax.set_title("校园每日消费趋势")
ax.set_xlabel("日期")
ax.set_ylabel("消费金额（元）")
ax.grid(axis="y", linestyle="--", alpha=0.4)
tick_step = max(1, (len(date_labels) + 11) // 12)
tick_positions = x_positions[::tick_step]
ax.set_xticks(tick_positions)
ax.set_xticklabels(date_labels[::tick_step], rotation=45, ha="right")
save_chart(fig, "每日消费趋势.png")

student_labels = student_top10.index.tolist()
student_values = student_top10.values
fig, ax = plt.subplots(figsize=(9, 6))
student_bars = ax.barh(student_labels, student_values, color="#4C78A8")
ax.set_title("学生消费排行榜 Top 10")
ax.set_xlabel("消费金额（元）")
ax.set_ylabel("学生 ID")
ax.invert_yaxis()
for bar, amount in zip(student_bars, student_values):
    ax.text(
        bar.get_width(),
        bar.get_y() + bar.get_height() / 2,
        " {:.2f}".format(amount),
        ha="left",
        va="center",
        fontsize=8,
    )
ax.set_xlim(0, max(student_values) * 1.18)
save_chart(fig, "学生消费排行榜.png")

fig, ax = plt.subplots(figsize=(8, 6))
wedges, unused_texts, unused_auto_texts = ax.pie(
    type_total.values,
    labels=None,
    autopct=lambda percentage: "{:.1f}%".format(percentage) if percentage >= 5 else "",
    startangle=90,
    pctdistance=0.72,
)
ax.set_title("消费类型占比")
ax.axis("equal")
ax.legend(
    wedges,
    type_total.index,
    title="消费类型",
    loc="center left",
    bbox_to_anchor=(1.0, 0.5),
)
save_chart(fig, "消费类型占比.png")

payment_labels = payment_count_ranking.index.tolist()
payment_values = payment_count_ranking.values
payment_positions = list(range(len(payment_labels)))
fig, ax = plt.subplots(figsize=(8, 5))
payment_bars = ax.bar(payment_positions, payment_values, color="#59A14F")
ax.set_title("支付方式使用情况")
ax.set_xlabel("支付方式")
ax.set_ylabel("使用次数")
ax.set_xticks(payment_positions)
ax.set_xticklabels(payment_labels)
ax.set_ylim(0, max(payment_values) * 1.15)
for bar, usage_count in zip(payment_bars, payment_values):
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height(),
        str(int(usage_count)),
        ha="center",
        va="bottom",
    )
save_chart(fig, "支付方式统计.png")

fig, axes = plt.subplots(1, 2, figsize=(10, 4.8))
axes[0].bar(day_type_order, day_type_daily_average.values, color=["#4C78A8", "#F28E2B"])
axes[0].set_title("工作日与周末日均消费金额")
axes[0].set_ylabel("金额（元）")
axes[1].bar(day_type_order, day_type_average.values, color=["#4C78A8", "#F28E2B"])
axes[1].set_title("工作日与周末平均每笔消费")
axes[1].set_ylabel("金额（元）")
save_chart(fig, "工作日周末消费对比.png")

month_positions = list(range(len(monthly_total.index)))
fig, ax = plt.subplots(figsize=(9, 5))
bars = ax.bar(month_positions, monthly_total.values, color="#76B7B2", alpha=0.9)
ax.set_title("月度消费趋势")
ax.set_xlabel("月份")
ax.set_ylabel("消费金额（元）")
ax.set_xticks(month_positions)
ax.set_xticklabels(monthly_total.index.tolist())
for bar, amount in zip(bars, monthly_total.values):
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height(),
        "{:.0f}".format(amount),
        ha="center",
        va="bottom",
        fontsize=8,
    )
ax.set_ylim(0, max(monthly_total.values) * 1.15)
save_chart(fig, "月度消费趋势.png")

weekday_labels = [weekday_names[index] for index in range(7)]
fig, ax = plt.subplots(figsize=(9, 5))
ax.bar(weekday_labels, weekday_total.values, color="#B279A2")
ax.set_title("星期消费金额分布")
ax.set_xlabel("星期")
ax.set_ylabel("消费金额（元）")
save_chart(fig, "星期消费分布.png")

print("\n================================")
print("分析完成！")
print("================================")
