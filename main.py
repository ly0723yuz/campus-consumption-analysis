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
# 消费类型柱状图
# ==============================

plt.figure(figsize=(8, 5))
type_total.plot(kind="bar")
plt.title("校园消费类型统计")
plt.xlabel("消费类型")
plt.ylabel("消费金额（元）")
plt.xticks(rotation=0)
plt.tight_layout()

type_chart_path = os.path.join(project_dir, "消费类型统计.png")
plt.savefig(type_chart_path)
print("\n图表已生成：消费类型统计.png")

# ==============================
# 每日消费趋势折线图
# ==============================

date_labels = [date.strftime("%Y-%m-%d") for date in daily_total.index]
x_positions = list(range(len(date_labels)))

plt.figure(figsize=(9, 5))
plt.plot(x_positions, daily_total.values, marker="o")
plt.title("校园每日消费趋势")
plt.xlabel("日期")
plt.ylabel("消费金额（元）")
plt.grid(axis="y", linestyle="--", alpha=0.5)

# 日期较多时减少显示的刻度，避免标签严重重叠
tick_step = max(1, len(date_labels) // 10)
tick_positions = x_positions[::tick_step]
tick_labels = date_labels[::tick_step]
plt.xticks(tick_positions, tick_labels, rotation=45, ha="right")
plt.tight_layout()

trend_chart_path = os.path.join(project_dir, "每日消费趋势.png")
plt.savefig(trend_chart_path)
print("图表已生成：每日消费趋势.png")

plt.show()

print("\n================================")
print("分析完成！")
print("================================")
