"""Create a blank, local 30-row title spot-check workbook."""
import csv
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs/review_table.csv"
TARGET = ROOT / "outputs/spotcheck_30.xlsx"


def main():
    if TARGET.exists():
        print("Keeping existing spot-check workbook; no judgments overwritten")
        return
    with SOURCE.open(encoding="utf-8-sig", newline="") as stream:
        source = list(csv.DictReader(stream))
    queries = list(dict.fromkeys(row["query"] for row in source))
    if len(queries) != 10:
        raise ValueError(f"Expected 10 queries, found {len(queries)}")
    selected = []
    for query in queries:
        rows = sorted((r for r in source if r["query"] == query),
                      key=lambda r: (-int(r["exposures"]), int(r["item_id"])))
        if len(rows) < 10:
            raise ValueError(f"{query}: fewer than 10 items")
        selected.extend(rows[i] for i in (0, 4, 9))

    wb = Workbook()
    ws = wb.active
    ws.title = "抽检表"
    ws.append(["query", "item_title", "category_level1", "category_level2", "exposures",
               "clicks", "item_ctr", "我的判断", "我的理由", "与自动预筛是否冲突", "自动预筛（二字覆盖率）", "已核对（填 Y）"])
    for row in selected:
        ws.append([row[k] for k in ("query", "item_title", "category_level1", "category_level2")]
                  + [int(row["exposures"]), int(row["clicks"]), float(row["item_ctr"]),
                     None, None, None, float(row["bigram_coverage"]), None])
        n = ws.max_row
        # Heuristic disagreement is a triage flag, never a relevance judgment.
        ws[f"J{n}"] = f'=IF(H{n}="","",IF(OR(AND(H{n}=0,K{n}>0),AND(H{n}=1,K{n}=0)),"是","否"))'
        ws[f"G{n}"].number_format = "0.00%"
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="285A75")
        cell.alignment = Alignment(wrap_text=True)
    for col, width in {"A":18,"B":62,"C":18,"D":18,"E":12,"F":10,"G":12,"H":12,"I":34,"J":24,"K":24}.items():
        ws.column_dimensions[col].width = width
    ws.freeze_panes = "B2"
    ws.auto_filter.ref = "A1:K31"
    dv = DataValidation(type="list", formula1='"1,0.5,0"', allow_blank=True)
    dv.error = "只能填 1、0.5 或 0"
    dv.showErrorMessage = True
    ws.add_data_validation(dv)
    dv.add("H2:H31")
    confirm = DataValidation(type="list", formula1='"Y"', allow_blank=True)
    confirm.showErrorMessage = True
    ws.add_data_validation(confirm)
    confirm.add('L2:L31')
    ws.column_dimensions['L'].width = 20
    notes = wb.create_sheet("说明")
    notes["A1"] = "标题抽检说明（预计 20 分钟）"
    notes["A2"] = "只看标题能否支撑用户判断；类目作辅助。不要依据价格、图片、销量判断。"
    notes["A3"] = "1：标题信息足以判断符合查询；0.5：方向相关但关键属性不足；0：明显不符。"
    notes["A4"] = "请逐行填写判断、理由并在L列填Y；完成后由实际审阅者提供reviewer_confirmation.json。"
    notes["A5"] = "自动预筛只比较查询与标题的二字片段；冲突列仅提示复看。"
    notes.column_dimensions["A"].width = 100
    TARGET.parent.mkdir(exist_ok=True)
    wb.save(TARGET)
    print(f"Created blank {TARGET.relative_to(ROOT)}: {len(selected)} rows, {len(queries)} queries")


if __name__ == "__main__":
    main()
