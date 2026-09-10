import csv
import datetime
import math
import os
import random


RANDOM_SEED = 20260910
RECORD_COUNT = 2000
STUDENT_COUNT = 120
START_DATE = datetime.date(2026, 3, 1)
END_DATE = datetime.date(2026, 6, 30)

CONSUMPTION_TYPES = [
    "食堂",
    "超市",
    "水果店",
    "饮料",
    "图书文具",
    "打印复印",
    "校园交通",
    "体育健身",
]

WEEKDAY_TYPE_WEIGHTS = [0.46, 0.15, 0.10, 0.08, 0.08, 0.06, 0.05, 0.02]
WEEKEND_TYPE_WEIGHTS = [0.25, 0.28, 0.13, 0.08, 0.08, 0.02, 0.07, 0.09]

# 每类消费采用不同的典型金额、波动和合理上下限。
AMOUNT_RULES = {
    "食堂": (16.0, 5.0, 5.0, 38.0),
    "超市": (34.0, 16.0, 6.0, 120.0),
    "水果店": (18.0, 7.0, 4.0, 55.0),
    "饮料": (7.0, 2.5, 2.0, 20.0),
    "图书文具": (28.0, 18.0, 3.0, 130.0),
    "打印复印": (5.0, 3.5, 0.5, 25.0),
    "校园交通": (3.0, 1.4, 1.0, 10.0),
    "体育健身": (45.0, 24.0, 8.0, 160.0),
}


def date_range(start_date, end_date):
    """返回包含起止日期的日期列表。"""
    days = (end_date - start_date).days
    return [start_date + datetime.timedelta(days=index) for index in range(days + 1)]


def weighted_choice(values, weights):
    """兼容 Python 3.7 的单次加权抽样。"""
    return random.choices(values, weights=weights, k=1)[0]


def allocate_daily_counts(dates, total_count):
    """按校历规律分配每日记录数，并保证总数精确。"""
    raw_weights = []
    for current_date in dates:
        is_weekend = current_date.weekday() >= 5
        base_weight = 0.58 if is_weekend else 1.0

        # 临近期末时校园活动和复习相关消费略有增加。
        if current_date.month == 6 and current_date.day >= 10:
            base_weight *= 1.12
        # 每日保留小幅自然波动，但仍受工作日/周末结构控制。
        base_weight *= random.uniform(0.88, 1.12)
        raw_weights.append(base_weight)

    weight_total = sum(raw_weights)
    exact_counts = [total_count * weight / weight_total for weight in raw_weights]
    counts = [max(1, int(math.floor(value))) for value in exact_counts]

    difference = total_count - sum(counts)
    fractions = [value - math.floor(value) for value in exact_counts]
    if difference > 0:
        order = sorted(range(len(dates)), key=lambda i: fractions[i], reverse=True)
        for index in order[:difference]:
            counts[index] += 1
    elif difference < 0:
        order = sorted(range(len(dates)), key=lambda i: fractions[i])
        remaining = -difference
        for index in order:
            if remaining == 0:
                break
            if counts[index] > 1:
                counts[index] -= 1
                remaining -= 1

    return counts


def build_student_profiles(student_ids):
    """为学生建立稳定的活跃度、消费能力和支付偏好。"""
    profiles = {}
    preferred_methods = ["微信", "支付宝", "校园卡", "银行卡"]
    preferred_weights = [0.40, 0.30, 0.25, 0.05]

    for student_id in student_ids:
        profiles[student_id] = {
            "activity": min(2.2, max(0.45, random.lognormvariate(0.0, 0.38))),
            "spend_factor": min(1.35, max(0.75, random.lognormvariate(0.0, 0.16))),
            "preferred_payment": weighted_choice(preferred_methods, preferred_weights),
        }
    return profiles


def choose_consumption_type(current_date):
    is_weekend = current_date.weekday() >= 5
    weights = list(WEEKEND_TYPE_WEIGHTS if is_weekend else WEEKDAY_TYPE_WEIGHTS)

    # 期末复习阶段提高图书文具、打印复印和饮料的出现概率。
    if current_date.month == 6 and current_date.day >= 10:
        weights[4] *= 1.65
        weights[5] *= 1.90
        weights[3] *= 1.20

    return weighted_choice(CONSUMPTION_TYPES, weights)


def generate_amount(consumption_type, spend_factor, current_date):
    mean, standard_deviation, minimum, maximum = AMOUNT_RULES[consumption_type]
    amount = random.gauss(mean, standard_deviation) * spend_factor

    if current_date.weekday() >= 5 and consumption_type in ("超市", "水果店", "体育健身"):
        amount *= 1.12
    if current_date.month == 6 and current_date.day >= 10 and consumption_type in ("图书文具", "打印复印"):
        amount *= 1.08

    amount = min(maximum, max(minimum, amount))
    return round(amount, 2)


def choose_payment_method(consumption_type, amount, preferred_payment):
    methods = ["微信", "支付宝", "校园卡", "银行卡"]
    weights = {"微信": 0.34, "支付宝": 0.28, "校园卡": 0.30, "银行卡": 0.08}

    weights[preferred_payment] *= 2.2

    if consumption_type in ("食堂", "打印复印", "校园交通"):
        weights["校园卡"] *= 1.8
    if amount >= 60:
        weights["支付宝"] *= 1.25
        weights["银行卡"] *= 1.55
        weights["校园卡"] *= 0.60

    return weighted_choice(methods, [weights[method] for method in methods])


def generate_records():
    random.seed(RANDOM_SEED)

    dates = date_range(START_DATE, END_DATE)
    daily_counts = allocate_daily_counts(dates, RECORD_COUNT)
    student_ids = ["S{:03d}".format(index) for index in range(1, STUDENT_COUNT + 1)]
    profiles = build_student_profiles(student_ids)

    # 每名学生至少出现一次，其余记录按活跃度抽样。
    assigned_students = list(student_ids)
    assigned_students.extend(random.choices(
        student_ids,
        weights=[profiles[student_id]["activity"] for student_id in student_ids],
        k=RECORD_COUNT - STUDENT_COUNT,
    ))
    random.shuffle(assigned_students)

    records = []
    student_position = 0
    for current_date, daily_count in zip(dates, daily_counts):
        for unused_index in range(daily_count):
            student_id = assigned_students[student_position]
            student_position += 1
            profile = profiles[student_id]

            consumption_type = choose_consumption_type(current_date)
            amount = generate_amount(
                consumption_type,
                profile["spend_factor"],
                current_date,
            )
            payment_method = choose_payment_method(
                consumption_type,
                amount,
                profile["preferred_payment"],
            )

            records.append([
                current_date.strftime("%Y-%m-%d"),
                student_id,
                consumption_type,
                "{:.2f}".format(amount),
                payment_method,
            ])

    return records


def main():
    project_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(project_dir, "data.csv")
    records = generate_records()

    with open(output_path, "w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["日期", "学生ID", "消费类型", "消费金额", "支付方式"])
        writer.writerows(records)

    print("模拟数据已生成：{}".format(output_path))
    print("固定随机种子：{}".format(RANDOM_SEED))
    print("记录数：{} 条".format(len(records)))
    print("学生数：{} 人".format(len(set(record[1] for record in records))))
    print("日期范围：{} 至 {}".format(START_DATE, END_DATE))


if __name__ == "__main__":
    main()
