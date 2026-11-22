"""Publish aggregate spot-check results only after every manual judgment is filled."""
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs/spotcheck_30.xlsx"
PUBLIC = ROOT / "outputs_public/spotcheck_summary.csv"
SECTION = ROOT / "outputs/spotcheck_section.md"
ATTR = [r"春秋|夏季|冬季|春夏|秋冬|加绒|加厚|薄款|新款|20\d{2}",
        r"宽松|修身|显瘦|大码|中长款|短款|长款|高腰|直筒|阔腿",
        r"棉|真丝|羊绒|羊毛|牛皮|真皮|涤纶|针织|雪纺|牛仔|皮革|硅胶|铝合金",
        r"(?i)pro|max|plus|mini|ultra|air|\d{2,4}\s*(码|号|寸|ml|g|kg|cm|mm)"]


def main():
    confirmation = ROOT / "outputs/reviewer_confirmation.json"
    if not confirmation.exists():
        raise ValueError("Missing author confirmation: outputs/reviewer_confirmation.json; no summary written")
    provenance = json.loads(confirmation.read_text(encoding="utf-8"))
    if not provenance.get("reviewer") or not provenance.get("reviewed_at") or provenance.get("personally_reviewed_all_30") is not True:
        raise ValueError("Author must confirm all 30 rows personally; no summary written")
    ws = load_workbook(SOURCE, data_only=False)["抽检表"]
    header = [cell.value for cell in ws[1]]
    if "已核对（填 Y）" not in header:
        raise ValueError("Missing mandatory confirmation column")
    confirm_index = header.index("已核对（填 Y）")
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    if len(rows) != 30:
        raise ValueError(f"Expected 30 rows, found {len(rows)}; no summary written")
    groups = defaultdict(list)
    with (ROOT / 'outputs/review_table.csv').open(encoding='utf-8-sig', newline='') as stream:
        source_rows = list(csv.DictReader(stream))
    expected = []
    for query in dict.fromkeys(r['query'] for r in source_rows):
        candidates = sorted([r for r in source_rows if r['query']==query], key=lambda r:(-int(r['exposures']),int(r['item_id'])))
        if len(candidates)<10:raise ValueError('Review source has fewer than ten products per query')
        expected.extend(candidates[i] for i in (0,4,9))
    actual_keys = [(r[0],r[1],int(r[4]),int(r[5])) for r in rows]
    expected_keys = [(r['query'],r['item_title'],int(r['exposures']),int(r['clicks'])) for r in expected]
    if actual_keys != expected_keys:
        raise ValueError('Workbook rows do not match exposure ranks 1/5/10; no summary written')
    for n, row in enumerate(rows, 2):
        query, title, judgment, reason = row[0], row[1], row[7], row[8]
        if judgment is None or str(judgment).strip() == "":
            raise ValueError(f"Row {n}: 我的判断 is blank; no summary written")
        if str(judgment).strip() not in ("1", "0.5", "0"):
            raise ValueError(f"Row {n}: invalid judgment {judgment!r}")
        if reason is None or not str(reason).strip():
            raise ValueError(f"Row {n}: 我的理由 is blank; no summary written")
        if confirm_index is not None and str(row[confirm_index] or "").strip().upper() != "Y":
            raise ValueError(f"Row {n}: 未勾选确认（L 列填 Y）；no summary written")
        if not query or not title:
            raise ValueError(f"Row {n}: query/title missing")
        groups[query].append((str(judgment).strip(), sum(bool(re.search(p, title)) for p in ATTR)))
    if len(groups) != 10 or any(len(v) != 3 for v in groups.values()):
        raise ValueError("Expected exactly three rows for each of ten queries")
    summary = []
    for query, values in groups.items():
        counts = {v: sum(score == v for score, _ in values) for v in ("1", "0.5", "0")}
        summary.append([query, 3, counts["1"], counts["0.5"], counts["0"],
                        format(sum(n for _, n in values) / 3, ".10g")])
    PUBLIC.parent.mkdir(exist_ok=True)
    with PUBLIC.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["query", "抽检数", "1计数", "0.5计数", "0计数", "avg_attribute_types"])
        writer.writerows(summary)
    totals = [sum(row[i] for row in summary) for i in (2, 3, 4)]
    lines = ["### 项目作者抽检 30 条（每词 3 条）", "", "仅检查标题能否支撑用户判断；每词按曝光量取第 1、5、10 名。", "",
             "| 搜索词 | 抽检数 | 1 | 0.5 | 0 | 平均属性类型数 |", "| --- | ---: | ---: | ---: | ---: | ---: |"]
    lines += [f"| {q} | {n} | {a} | {b} | {c} | {avg} |" for q,n,a,b,c,avg in summary]
    lines += ["", f"结论模板：30 条中 1/0.5/0 分别为 {totals[0]}/{totals[1]}/{totals[2]} 条；这些高曝光样本提示【请项目作者结合理由填写具体发现】，不外推为全部商品相关率。", ""]
    SECTION.write_text("\n".join(lines), encoding="utf-8")
    print("Wrote aggregate summary and report section for 30 manually judged rows")


if __name__ == "__main__":
    main()
