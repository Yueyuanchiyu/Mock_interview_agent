from __future__ import annotations

import argparse
import sys
from pathlib import Path

from openpyxl import load_workbook


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.infrastructure.db import get_conn  # noqa: E402


def read_rows(path: Path):
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        sheet = workbook.active
        rows = []
        for index, row in enumerate(sheet.iter_rows(values_only=True), start=1):
            values = [str(item or "").strip() for item in row[:8]]
            values.extend([""] * (8 - len(values)))
            if index == 1 and values[0].lower() in {"role_code", "岗位编码"}:
                continue
            if not any(values):
                continue
            rows.append(tuple(values))
        return rows
    finally:
        workbook.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="导入题库 Excel")
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    rows = read_rows(args.path)
    sql = """
        INSERT INTO question_bank
            (role_code, question_type, difficulty, title, reference_answer,
             scoring_points, followup_points, tags)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    normalized = []
    for row in rows:
        role_code, question_type, difficulty, *rest = row
        try:
            difficulty_value = int(float(difficulty or 1))
        except ValueError:
            difficulty_value = 1
        normalized.append((role_code, question_type, difficulty_value, *rest))

    with get_conn() as conn:
        with conn.cursor() as cursor:
            cursor.executemany(sql, normalized)
    print(f"导入完成：{len(normalized)} 条")


if __name__ == "__main__":
    main()

