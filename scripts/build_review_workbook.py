"""Build the human review workbook (Excel) for the P3 evidence chain.

Sheets
------
说明        how to fill it, what each column means, how long it takes
审阅表      one row per query x product, with a 1 / 0.5 / 0 dropdown
词级汇总    per-query automatic evidence: dispersion, concentration, attribute coverage

The workbook contains item titles, so it stays in outputs/ (local, not published).
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".localdeps"))
import duckdb

REVIEW = ROOT / "outputs" / "review_table.csv"
DB = ROOT / "data" / "processed" / "kuaisearch.duckdb"
TARGET = ROOT / "outputs" / "review_workbook.xlsx"

ATTR_PATTERNS = {
    "season": r"春秋|夏季|冬季|春夏|秋冬|加绒|加厚|薄款|新款|20\d{2}",
    "fit": r"宽松|修身|显瘦|大码|中长款|短款|长款|高腰|直筒|阔腿",
    "material": r"棉|真丝|羊绒|羊毛|牛皮|真皮|涤纶|针织|雪纺|牛仔|皮革|硅胶|铝合金",
    "model": r"(?i)pro|max|plus|mini|ultra|air|\d{2,4}\s*(码|号|寸|ml|g|kg|cm|mm)",
}

NOTES = """审阅说明（约 20–30 分钟可完成）

1. 打开「审阅表」，只填最后两列：
   human_relevance —— 1 = 商品符合这个搜索意图；0.5 = 相关但信息不足；0 = 不符合
   human_note      —— 一句话说明（可选，例如「类目错」「缺机型」「标题只有品类」）
2. 判断依据只看「用户能不能仅凭标题判断这件商品是不是自己要的」：
   - 标题里有用户 query 指向的具体属性（版型/材质/季节/型号）→ 1
   - 只有品类词，没有任何可判断的属性 → 0.5
   - 类目或属性明显不对 → 0
3. 不要用「这个商品好不好」代替「是否符合这个搜索」。价格、图片、销量不在表里。
4. 填完后看「词级汇总」：
   - 类目分散度高（distinct_category1 ≥ 3）+ 高曝光商品零相关 → 供给/类目问题
   - 品牌集中度极高且都是同款 → 可能是铺货，优先查标题信息
   - 属性覆盖低（avg_attribute_types < 1）→ 商品信息补全动作优先
   - 点击集中在前 10 位（click_share_top10 很高）→ 结果页结构动作优先

口径与判读规则见 docs/evidence-review.md；数据口径见 docs/metrics.md。
"""


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def attribute_stats(title: str) -> tuple[int, int]:
    hits = 0
    types = 0
    for pattern in ATTR_PATTERNS.values():
        found = re.findall(pattern, title or "")
        if found:
            types += 1
            hits += len(found)
    return types, hits


def click_concentration(conn, queries: list[str]) -> dict[str, tuple[float, float, float]]:
    placeholders = ", ".join("?" for _ in queries)
    rows = conn.execute(
        f"""
        SELECT
          s.query,
          sum(f.is_clicked) AS clicks,
          sum(f.is_clicked) FILTER (WHERE f.position <= 10) AS clicks_top10,
          sum(f.is_clicked) FILTER (WHERE f.position <= 20) AS clicks_top20,
          avg(f.position) FILTER (WHERE f.is_clicked = 1) AS mean_click_position
        FROM fact AS f
        JOIN sessions AS s USING (session_id)
        WHERE f.split = 'train' AND s.query IN ({placeholders})
        GROUP BY s.query
        """,
        queries,
    ).fetchall()
    result = {}
    for query, clicks, top10, top20, mean_pos in rows:
        clicks = clicks or 0
        result[query] = (
            (top10 or 0) / clicks if clicks else 0.0,
            (top20 or 0) / clicks if clicks else 0.0,
            float(mean_pos or 0),
        )
    return result


def main() -> None:
    rows = read_csv(REVIEW)
    queries = []
    for row in rows:
        if row["query"] not in queries:
            queries.append(row["query"])

    conn = duckdb.connect(str(DB), read_only=True)
    try:
        click_stats = click_concentration(conn, queries)
    finally:
        conn.close()

    # per-query aggregation of the reviewed products
    summary: list[dict] = []
    for query in queries:
        items = [row for row in rows if row["query"] == query]
        exposures = sum(int(row["exposures"]) for row in items)
        clicks = sum(int(row["clicks"]) for row in items)
        categories = {row["category_level1"] for row in items}
        brands = {row["brand_name"] for row in items if row["brand_name"]}
        category_counts: dict[str, int] = {}
        brand_counts: dict[str, int] = {}
        for row in items:
            category_counts[row["category_level1"]] = category_counts.get(row["category_level1"], 0) + 1
            if row["brand_name"]:
                brand_counts[row["brand_name"]] = brand_counts.get(row["brand_name"], 0) + 1
        attr_types = [attribute_stats(row["item_title"])[0] for row in items]
        attr_hits = [attribute_stats(row["item_title"])[1] for row in items]
        top10, top20, mean_pos = click_stats.get(query, (0.0, 0.0, 0.0))
        first = items[0]
        summary.append(
            {
                "rank": first["rank"],
                "query": query,
                "gap_pp": round(float(first["gap_pp"]), 3),
                "gap_clicks": round(float(first["gap_clicks"]), 1),
                "items_reviewed": len(items),
                "exposures_reviewed": exposures,
                "clicks_reviewed": clicks,
                "reviewed_ctr_pct": round(clicks / exposures * 100, 3) if exposures else 0.0,
                "avg_bigram_coverage": round(
                    sum(float(row["bigram_coverage"]) for row in items) / len(items), 3
                ),
                "distinct_category1": len(categories),
                "top1_category_share": round(max(category_counts.values()) / len(items), 3),
                "distinct_brands": len(brands),
                "top1_brand_share": round(max(brand_counts.values()) / len(items), 3) if brand_counts else 0.0,
                "avg_attribute_types": round(sum(attr_types) / len(attr_types), 2),
                "avg_attribute_hits": round(sum(attr_hits) / len(attr_hits), 2),
                "share_titles_with_attribute": round(sum(1 for value in attr_types if value > 0) / len(items), 3),
                "click_share_top10": round(top10, 3),
                "click_share_top20": round(top20, 3),
                "mean_click_position": round(mean_pos, 2),
            }
        )

    workbook = Workbook()
    notes = workbook.active
    notes.title = "说明"
    notes["A1"] = NOTES
    notes["A1"].alignment = Alignment(wrap_text=True, vertical="top")
    notes.column_dimensions["A"].width = 100
    for row_index in range(1, 24):
        notes.row_dimensions[row_index].height = 22

    review_sheet = workbook.create_sheet("审阅表")
    headers = [
        "rank",
        "query",
        "item_rank",
        "item_id",
        "item_title",
        "brand_name",
        "category_level1",
        "category_level2",
        "exposures",
        "clicks",
        "item_ctr",
        "avg_position",
        "bigram_coverage",
        "human_relevance",
        "human_note",
    ]
    review_sheet.append(headers)
    for cell in review_sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="2F6FDD")
        cell.alignment = Alignment(horizontal="center")
    for row in rows:
        review_sheet.append(
            [
                int(row["rank"]),
                row["query"],
                int(row["item_rank"]),
                int(row["item_id"]),
                row["item_title"],
                row["brand_name"],
                row["category_level1"],
                row["category_level2"],
                int(row["exposures"]),
                int(row["clicks"]),
                round(float(row["item_ctr"]) * 100, 3),
                float(row["avg_position"]),
                float(row["bigram_coverage"]),
                None,
                None,
            ]
        )
    widths = [6, 16, 8, 11, 52, 16, 16, 14, 10, 8, 9, 11, 12, 14, 30]
    for index, width in enumerate(widths, start=1):
        review_sheet.column_dimensions[get_column_letter(index)].width = width
    review_sheet.freeze_panes = "C2"
    review_sheet.auto_filter.ref = f"A1:O{review_sheet.max_row}"
    validation = DataValidation(type="list", formula1='"1,0.5,0"', allow_blank=True, showDropDown=False)
    validation.error = "请填 1 / 0.5 / 0"
    validation.errorTitle = "取值不合法"
    review_sheet.add_data_validation(validation)
    validation.add(f"N2:N{review_sheet.max_row}")
    for r in range(2, review_sheet.max_row + 1):
        review_sheet[f"K{r}"].number_format = "0.000"

    summary_sheet = workbook.create_sheet("词级汇总")
    summary_sheet.append(list(summary[0].keys()))
    for cell in summary_sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="2F6FDD")
    for item in summary:
        summary_sheet.append(list(item.values()))
    for index in range(1, len(summary[0]) + 1):
        summary_sheet.column_dimensions[get_column_letter(index)].width = 18
    summary_sheet.freeze_panes = "A2"

    workbook.save(TARGET)
    print(f"wrote {TARGET.relative_to(ROOT)}")
    print("query  gap_pp  cat1  top1_cat  brands  top1_brand  attr_types  click<=10")
    for item in summary:
        print(
            f"{item['query']:<12} {item['gap_pp']:>6.2f} {item['distinct_category1']:>4} "
            f"{item['top1_category_share']:>9.2f} {item['distinct_brands']:>7} "
            f"{item['top1_brand_share']:>10.2f} {item['avg_attribute_types']:>10.2f} "
            f"{item['click_share_top10']:>10.2f}"
        )


if __name__ == "__main__":
    main()
