import csv
import datetime
import math
import os
import sqlite3


DATABASE_FILENAME = "campus_consumption.db"
TABLE_NAME = "consumption_records"
CSV_COLUMNS = ["日期", "学生ID", "消费类型", "消费金额", "支付方式"]


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS consumption_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    student_id TEXT NOT NULL,
    category TEXT NOT NULL,
    amount REAL NOT NULL CHECK (amount > 0),
    payment_method TEXT NOT NULL
)
"""


def create_connection(database_path):
    """创建并返回 SQLite 数据库连接。"""
    try:
        return sqlite3.connect(database_path)
    except sqlite3.Error as error:
        print("数据库连接失败：{}".format(error))
        raise


def create_consumption_table(connection):
    """创建消费记录表和常用查询索引。"""
    connection.execute(CREATE_TABLE_SQL)
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_consumption_date "
        "ON consumption_records (date)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_consumption_student "
        "ON consumption_records (student_id)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_consumption_category "
        "ON consumption_records (category)"
    )
    connection.commit()


def validate_csv_row(row, line_number):
    """验证一行 CSV 数据，并转换为数据库需要的字段类型。"""
    values = []
    for column in CSV_COLUMNS:
        value = row.get(column)
        if value is None or str(value).strip() == "":
            raise ValueError("第 {} 行的“{}”为空".format(line_number, column))
        values.append(str(value).strip())

    date_text, student_id, category, amount_text, payment_method = values

    try:
        parsed_date = datetime.datetime.strptime(date_text, "%Y-%m-%d")
    except ValueError:
        raise ValueError(
            "第 {} 行的日期格式错误，应为 YYYY-MM-DD".format(line_number)
        )

    if parsed_date.strftime("%Y-%m-%d") != date_text:
        raise ValueError("第 {} 行的日期不是有效日期".format(line_number))

    try:
        amount = float(amount_text)
    except ValueError:
        raise ValueError("第 {} 行的消费金额不是数字".format(line_number))

    if not math.isfinite(amount) or amount <= 0:
        raise ValueError("第 {} 行的消费金额必须为正数".format(line_number))

    return date_text, student_id, category, amount, payment_method


def read_validated_csv(csv_path):
    """读取并验证 CSV，验证通过后返回全部待导入记录。"""
    records = []
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames != CSV_COLUMNS:
            actual_columns = reader.fieldnames or []
            raise ValueError(
                "CSV 字段不正确。应为：{}；实际为：{}".format(
                    "、".join(CSV_COLUMNS),
                    "、".join(actual_columns),
                )
            )

        for line_number, row in enumerate(reader, start=2):
            records.append(validate_csv_row(row, line_number))

    if not records:
        raise ValueError("CSV 中没有可导入的消费记录")

    return records


def import_csv_to_database(connection, csv_path):
    """清空旧数据后导入 CSV，保证重复运行不会不断追加。"""
    records = read_validated_csv(csv_path)
    insert_sql = """
    INSERT INTO consumption_records (
        date, student_id, category, amount, payment_method
    ) VALUES (?, ?, ?, ?, ?)
    """

    # 先完成全部 CSV 验证，再在一个事务中删除和写入。
    # 如果插入失败，SQLite 会自动回滚，不会留下半份数据。
    with connection:
        connection.execute("DELETE FROM consumption_records")
        connection.execute(
            "DELETE FROM sqlite_sequence WHERE name = ?",
            (TABLE_NAME,),
        )
        connection.executemany(insert_sql, records)

    return len(records)


def execute_query(connection, sql, parameters=()):
    """执行基础 SELECT 查询并返回全部结果。"""
    try:
        cursor = connection.execute(sql, parameters)
        return cursor.fetchall()
    except sqlite3.Error as error:
        print("SQL 查询失败：{}".format(error))
        raise


def get_record_count(connection):
    """返回消费记录表的记录数。"""
    rows = execute_query(
        connection,
        "SELECT COUNT(*) FROM consumption_records",
    )
    return int(rows[0][0])


def close_connection(connection):
    """安全关闭数据库连接。"""
    if connection is not None:
        connection.close()


def refresh_database(csv_path, database_path):
    """创建数据库结构并用当前 CSV 完整刷新消费记录表。"""
    connection = None
    try:
        connection = create_connection(database_path)
        create_consumption_table(connection)
        imported_count = import_csv_to_database(connection, csv_path)
        database_count = get_record_count(connection)
        if imported_count != database_count:
            raise RuntimeError(
                "导入记录数与数据库记录数不一致：{} != {}".format(
                    imported_count, database_count
                )
            )
        return database_count
    except ValueError as error:
        print("CSV 数据验证失败：{}".format(error))
        raise
    except sqlite3.Error as error:
        print("数据库操作失败：{}".format(error))
        raise
    finally:
        close_connection(connection)


def main():
    project_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(project_dir, "data.csv")
    database_path = os.path.join(project_dir, DATABASE_FILENAME)
    record_count = refresh_database(csv_path, database_path)
    print("SQLite 数据库已更新：{}".format(database_path))
    print("consumption_records 表记录数：{}".format(record_count))


if __name__ == "__main__":
    main()
