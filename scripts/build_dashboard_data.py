"""Pack the public aggregates into one workbook for Power BI / Excel.

Power BI can import a multi-sheet Excel file with a single connection, which is the
fastest path for a beginner: `Get Data -> Excel workbook -> select all sheets`.
"""

from __future__ import annotations

import csv
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "outputs_public"
TARGET = ROOT / "dashboards" / "data" / "kuaisearch_dashboard.xlsx"

# sheet name -> (source csv, columns to format as percent)
SHEETS = [
    ("总览", "overview.csv", {"item_ctr", "request_click_rate", "request_purchase_rate"}),
    ("条数分层", "length_strata.csv", {"item_ctr", "request_click_rate"}),
    ("条数基准", "stratum_baseline.csv", {"item_ctr"}),
    ("类目", "category_metrics.csv", {"item_ctr", "item_purchase_rate"}),
    ("类目残差", "category_residuals.csv", {"item_ctr", "expected_ctr"}),
    ("需求标签", "intent_metrics.csv", {"item_ctr", "request_click_rate", "request_purchase_rate"}),
    ("需求残差", "intent_residuals.csv", {"item_ctr", "expected_ctr"}),
    (
        "机会清单",
        "opportunities_top30.csv",
        {"item_ctr", "expected_ctr", "request_click_rate", "request_purchase_rate", "test_item_ctr"},
    ),
    ("相对时间", "relative_time_metrics.csv", {"item_ctr", "request_click_rate"}),
    ("年龄", "age_metrics.csv", {"item_ctr", "request_click_rate"}),
    ("相关性覆盖", "relevance_coverage.csv", set()),
]

NOTES = """快手电商搜索需求与转化效率诊断 — 看板数据

口径：商品点击率 = 点击商品/曝光商品；请求点击率 = 有点击的请求/请求。
条数分层：按每次请求展示的商品条数分组；期望点击 = Σ(各层曝光 × 该层训练段基准 CTR)。
gap_pp 为百分点数值（1.47 表示 1.47pp），不是百分比，不要再乘 100。
数据为公开聚合结果，不含用户级明细。完整口径见 docs/metrics.md。
"""


def main() -> None:
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    notes = workbook.active
    notes.title = "说明"
    notes["A1"] = NOTES
    notes["A1"].alignment = Alignment(wrap_text=True, vertical="top")
    notes.column_dimensions["A"].width = 110

    for sheet_name, file_name, percent_columns in SHEETS:
        path = PUBLIC / file_name
        with path.open(encoding="utf-8-sig") as stream:
            rows = list(csv.reader(stream))
        sheet = workbook.create_sheet(sheet_name)
        for r, row in enumerate(rows, start=1):
            for c, value in enumerate(row, start=1):
                cell = sheet.cell(row=r, column=c, value=value)
                if r == 1:
                    cell.font = Font(bold=True, color="FFFFFF")
                    cell.fill = PatternFill("solid", fgColor="2F6FDD")
                    cell.alignment = Alignment(horizontal="center")
        header = rows[0]
        for index, name in enumerate(header, start=1):
            letter = get_column_letter(index)
            width = max(len(str(name)) * 2 + 4, 12)
            sheet.column_dimensions[letter].width = min(width, 42)
            if name in percent_columns:
                for r in range(2, len(rows) + 1):
                    sheet.cell(row=r, column=index).number_format = "0.00%"
            elif name.endswith("_pp"):
                for r in range(2, len(rows) + 1):
                    sheet.cell(row=r, column=index).number_format = "0.00"
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions

    workbook.save(TARGET)
    print(f"wrote {TARGET.relative_to(ROOT)} with {len(SHEETS) + 1} sheets")


if __name__ == "__main__":
    main()
