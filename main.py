import os

import pandas as pd
import matplotlib.pyplot as plt


# 设置中文字体，避免图表中的中文显示为方框
plt.rcParams["font.sans-serif"] = ["SimHei"]
plt.rcParams["axes.unicode_minus"] = False


print("================================")
print("      校园消费数据分析系统")
print("================================")

# 使用程序所在目录拼接文件路径，避免从其他目录运行时找不到文件
project_dir = os.path.dirname(os.path.abspath(__file__))
data_path = os.path.join(project_dir, "data.csv")

# 读取消费数据
data = pd.read_csv(data_path)

# ==============================
# 数据检查和清洗
# ==============================

required_columns = ["日期", "学生ID", "消费类型", "消费金额", "支付方式"]
missing_columns = [column for column in required_columns if column not in data.columns]

if missing_columns:
    raise ValueError("数据缺少必要字段：" + "、".join(missing_columns))

missing_value_count = int(data[required_columns].isnull().sum().sum())
duplicate_count = int(data.duplicated().sum())

# errors="coerce" 会将无法转换的金额变为缺失值，便于统一检查
original_amount = data["消费金额"]
converted_amount = pd.to_numeric(original_amount, errors="coerce")
invalid_amount_count = int((original_amount.notnull() & converted_amount.isnull()).sum())
data["消费金额"] = converted_amount

# 将日期转换为日期类型，无法转换的日期会变为缺失值
original_date = data["日期"]
converted_date = pd.to_datetime(original_date, errors="coerce")
invalid_date_count = int((original_date.notnull() & converted_date.isnull()).sum())
data["日期"] = converted_date

abnormal_amount_count = int((data["消费金额"] <= 0).sum())

print("\n【数据清洗】")
print("缺失值数量：", missing_value_count)
print("重复记录数量：", duplicate_count)
print("无法转换的消费金额：", invalid_amount_count)
print("异常消费记录（金额 <= 0）：", abnormal_amount_count)
print("日期格式异常记录：", invalid_date_count)

# 删除重复记录；仅删除缺少必要信息、格式错误或金额非正数的记录
data = data.drop_duplicates().copy()
before_clean_count = len(data)
data = data.dropna(subset=required_columns)
data = data[data["消费金额"] > 0].copy()
removed_count = before_clean_count - len(data)

print("本次清洗删除记录：", removed_count)
print("数据清洗完成")

if data.empty:
    raise ValueError("清洗后没有可用于分析的数据。")

# 按日期排序，便于预览和每日趋势分析
data = data.sort_values("日期")

print("\n【数据预览】")
print(data)

# ==============================
# 基本统计
# ==============================

total_amount = data["消费金额"].sum()
count = len(data)
average_amount = data["消费金额"].mean()
max_amount = data["消费金额"].max()
min_amount = data["消费金额"].min()

print("\n【基本统计】")
print("消费记录数：", count)
print("总消费金额：", round(total_amount, 2))
print("平均每笔消费：", round(average_amount, 2))
print("单笔最高消费金额：", round(max_amount, 2))
print("单笔最低消费金额：", round(min_amount, 2))

# 每个学生的消费总额
student_total = data.groupby("学生ID")["消费金额"].sum()

print("\n【学生消费统计】")
print(student_total)

# 学生消费金额排行榜，按总金额从高到低排列
student_ranking = student_total.sort_values(ascending=False)

print("\n【学生消费金额排行榜】")
for rank, (student_id, amount) in enumerate(student_ranking.items(), start=1):
    print("第{}名：{}，消费金额：{} 元".format(
        rank, student_id, round(amount, 2)
    ))

# 统计每个学生的消费次数；如果出现并列，显示所有并列学生
student_count = data.groupby("学生ID").size()
most_frequent_count = int(student_count.max())
most_frequent_students = student_count[
    student_count == most_frequent_count
].index.tolist()

print("\n【消费次数最多的学生】")
print("学生ID：", "、".join(most_frequent_students))
print("消费次数：", most_frequent_count)

# 各消费类型统计
type_total = data.groupby("消费类型")["消费金额"].sum()

print("\n【消费类型统计】")
print(type_total)

# 消费最高的学生
top_student = student_total.idxmax()
top_amount = student_total.max()

print("\n【消费最高学生】")
print("学生ID：", top_student)
print("消费金额：", round(top_amount, 2))

# ==============================
# 支付方式统计
# ==============================

payment_total = data.groupby("支付方式")["消费金额"].sum()
payment_count = data.groupby("支付方式").size()

print("\n【支付方式统计】")
for payment_method in payment_total.index:
    print("\n{}：".format(payment_method))
    print("使用次数：", int(payment_count[payment_method]))
    print("消费金额：{} 元".format(round(payment_total[payment_method], 2)))

# ==============================
# 每日消费趋势统计
# ==============================

daily_total = data.groupby("日期")["消费金额"].sum().sort_index()

print("\n【每日消费趋势】")
for date, amount in daily_total.items():
    print("{}：{} 元".format(date.strftime("%Y-%m-%d"), round(amount, 2)))

# ==============================
# 自动生成文字分析报告
# ==============================

student_number = data["学生ID"].nunique()
start_date = data["日期"].min().strftime("%Y-%m-%d")
end_date = data["日期"].max().strftime("%Y-%m-%d")

top_type = type_total.idxmax()
top_type_amount = type_total.max()
top_type_ratio = top_type_amount / total_amount * 100

max_payment_count = int(payment_count.max())
most_used_payments = payment_count[
    payment_count == max_payment_count
].index.tolist()

max_daily_amount = daily_total.max()
top_dates = daily_total[daily_total == max_daily_amount].index.tolist()
top_date_text = "、".join([
    date.strftime("%Y-%m-%d") for date in top_dates
])

report_lines = [
    "校园消费数据分析报告",
    "=" * 30,
    "",
    "一、数据基本情况",
    "数据记录数：{} 条".format(count),
    "学生数量：{} 人".format(student_number),
    "数据日期范围：{} 至 {}".format(start_date, end_date),
    "",
    "二、整体消费情况",
    "总消费金额：{:.2f} 元".format(total_amount),
    "平均每笔消费：{:.2f} 元".format(average_amount),
    "单笔最高消费：{:.2f} 元".format(max_amount),
    "单笔最低消费：{:.2f} 元".format(min_amount),
    "",
    "三、学生消费情况",
    "消费金额最高的学生：{}".format(top_student),
    "该学生的消费金额：{:.2f} 元".format(top_amount),
    "消费次数最多的学生：{}（{} 次）".format(
        "、".join(most_frequent_students), most_frequent_count
    ),
    "学生消费排行榜：",
]

for rank, (student_id, amount) in enumerate(student_ranking.items(), start=1):
    report_lines.append(
        "  第{}名：{}，{:.2f} 元".format(rank, student_id, amount)
    )

report_lines.extend([
    "",
    "四、消费类型分析",
    "各消费类型金额：",
])

for consumption_type, amount in type_total.sort_values(ascending=False).items():
    report_lines.append("  {}：{:.2f} 元".format(consumption_type, amount))

report_lines.extend([
    "消费金额最高的类型：{}".format(top_type),
    "该类型消费金额：{:.2f} 元".format(top_type_amount),
    "该类型约占总消费金额的 {:.1f}%".format(top_type_ratio),
    "",
    "五、支付方式分析",
    "各支付方式使用次数和消费金额：",
])

for payment_method in payment_count.sort_values(ascending=False).index:
    report_lines.append(
        "  {}：{} 次，{:.2f} 元".format(
            payment_method,
            int(payment_count[payment_method]),
            payment_total[payment_method],
        )
    )

report_lines.extend([
    "使用次数最多的支付方式：{}（{} 次）".format(
        "、".join(most_used_payments), max_payment_count
    ),
    "",
    "六、每日消费趋势",
    "每日消费金额：",
])

for date, amount in daily_total.items():
    report_lines.append(
        "  {}：{:.2f} 元".format(date.strftime("%Y-%m-%d"), amount)
    )

report_lines.extend([
    "消费金额最高的一天：{}，{:.2f} 元".format(
        top_date_text, max_daily_amount
    ),
    "",
    "七、简单总结",
    "从当前数据来看，学生消费主要集中在{}，该类别消费金额为{:.2f}元，"
    "约占总消费金额的{:.1f}%。".format(
        top_type, top_type_amount, top_type_ratio
    ),
    "消费金额最高的学生是{}，累计消费{:.2f}元。".format(
        top_student, top_amount
    ),
    "在支付方式方面，{}使用最频繁，共使用{}次。".format(
        "、".join(most_used_payments), max_payment_count
    ),
    "{}的消费金额最高，为{:.2f}元。".format(
        top_date_text, max_daily_amount
    ),
])

report_path = os.path.join(project_dir, "analysis_report.txt")
with open(report_path, "w", encoding="utf-8") as report_file:
    report_file.write("\n".join(report_lines))

print("\n分析报告已生成：analysis_report.txt")

# ==============================
# 消费类型柱状图
# ==============================

fig, ax = plt.subplots(figsize=(8, 5))
type_total.plot(kind="bar", ax=ax)
ax.set_title("校园消费类型统计")
ax.set_xlabel("消费类型")
ax.set_ylabel("消费金额（元）")
ax.tick_params(axis="x", rotation=0)
fig.tight_layout()

type_chart_path = os.path.join(project_dir, "消费类型统计.png")
fig.savefig(type_chart_path, dpi=150)
plt.close(fig)
print("\n图表已生成：消费类型统计.png")

# ==============================
# 每日消费趋势折线图
# ==============================

date_labels = [date.strftime("%Y-%m-%d") for date in daily_total.index]
x_positions = list(range(len(date_labels)))

fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(x_positions, daily_total.values, marker="o")
ax.set_title("校园每日消费趋势")
ax.set_xlabel("日期")
ax.set_ylabel("消费金额（元）")
ax.grid(axis="y", linestyle="--", alpha=0.5)

# 日期较多时减少显示的刻度，避免标签严重重叠
tick_step = max(1, (len(date_labels) + 9) // 10)
tick_positions = x_positions[::tick_step]
tick_labels = date_labels[::tick_step]
ax.set_xticks(tick_positions)
ax.set_xticklabels(tick_labels, rotation=45, ha="right")
fig.tight_layout()

trend_chart_path = os.path.join(project_dir, "每日消费趋势.png")
fig.savefig(trend_chart_path, dpi=150)
plt.close(fig)
print("图表已生成：每日消费趋势.png")

# ==============================
# 学生消费排行榜柱状图
# ==============================

student_labels = student_ranking.index.tolist()
student_values = student_ranking.values
student_positions = list(range(len(student_labels)))

fig, ax = plt.subplots(figsize=(8, 5))
student_bars = ax.bar(student_positions, student_values, color="#4C78A8")
ax.set_title("学生消费排行榜")
ax.set_xlabel("学生 ID")
ax.set_ylabel("消费金额（元）")
ax.set_xticks(student_positions)
ax.set_xticklabels(student_labels)

# 在柱子顶部显示消费金额
for bar, amount in zip(student_bars, student_values):
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height(),
        "{:.2f}".format(amount),
        ha="center",
        va="bottom",
    )

fig.tight_layout()
student_chart_path = os.path.join(project_dir, "学生消费排行榜.png")
fig.savefig(student_chart_path, dpi=150)
plt.close(fig)
print("图表已生成：学生消费排行榜.png")

# ==============================
# 消费类型占比饼图
# ==============================

fig, ax = plt.subplots(figsize=(8, 6))
ax.pie(
    type_total.values,
    labels=type_total.index,
    autopct="%1.1f%%",
    startangle=90,
    labeldistance=1.08,
    pctdistance=0.72,
)
ax.set_title("消费类型占比")
ax.axis("equal")
fig.tight_layout()

type_ratio_chart_path = os.path.join(project_dir, "消费类型占比.png")
fig.savefig(type_ratio_chart_path, dpi=150)
plt.close(fig)
print("图表已生成：消费类型占比.png")

# ==============================
# 支付方式使用次数柱状图
# ==============================

payment_count_ranking = payment_count.sort_values(ascending=False)
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

# 在柱子顶部显示使用次数
for bar, usage_count in zip(payment_bars, payment_values):
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height(),
        str(int(usage_count)),
        ha="center",
        va="bottom",
    )

fig.tight_layout()
payment_chart_path = os.path.join(project_dir, "支付方式统计.png")
fig.savefig(payment_chart_path, dpi=150)
plt.close(fig)
print("图表已生成：支付方式统计.png")

print("\n================================")
print("分析完成！")
print("================================")
