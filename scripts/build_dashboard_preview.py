"""Build a static, dependency-free dashboard preview (dashboards/preview.html).

It mirrors the five Power BI pages so the layout can be reviewed before the workbook
is rebuilt, and it doubles as a fallback portfolio page that needs no software.
All data comes from outputs_public/, so the file is safe to publish.
"""

from __future__ import annotations

import csv
import html
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "outputs_public"
TARGET = ROOT / "dashboards" / "preview.html"

BLUE = "#2f6fdd"
ORANGE = "#e8590c"
GREY = "#6b7280"
GRID = "#e5e7eb"
FONT = "'Segoe UI', 'Microsoft YaHei', 'PingFang SC', sans-serif"


def read(name: str) -> list[dict[str, str]]:
    with (PUBLIC / name).open(encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def fmt_pct(value: str | float, digits: int = 2) -> str:
    return f"{float(value) * 100:.{digits}f}%"


def fmt_int(value: str | float) -> str:
    return f"{int(float(value)):,}"


def vbars(rows: list[tuple[str, float]], width: int = 640, height: int = 300,
          color: str = BLUE, value_fmt: str = "{:.2f}%", y_label: str = "") -> str:
    left, right, top, bottom = 58, 18, 34, 54
    plot_w, plot_h = width - left - right, height - top - bottom
    peak = max(value for _, value in rows) * 1.18 or 1
    out = [f'<svg viewBox="0 0 {width} {height}" width="100%" role="img">']
    if y_label:
        out.append(f'<text x="4" y="16" font-size="10" fill="{GREY}">{html.escape(y_label)}</text>')
    for step in range(5):
        y = top + plot_h - plot_h * step / 4
        value = peak * step / 4
        out.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width - right}" y2="{y:.1f}" stroke="{GRID}"/>')
        out.append(f'<text x="{left - 8}" y="{y + 3:.1f}" font-size="10" fill="{GREY}" text-anchor="end">{value:.1f}%</text>')
    slot = plot_w / len(rows)
    for index, (label, value) in enumerate(rows):
        bar_h = plot_h * value / peak
        x = left + slot * index + slot * 0.18
        y = top + plot_h - bar_h
        out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{slot * 0.64:.1f}" height="{bar_h:.1f}" fill="{color}" rx="2"/>')
        out.append(f'<text x="{x + slot * 0.32:.1f}" y="{y - 6:.1f}" font-size="10" fill="#111827" text-anchor="middle">{value_fmt.format(value)}</text>')
        out.append(f'<text x="{x + slot * 0.32:.1f}" y="{top + plot_h + 16}" font-size="10" fill="{GREY}" text-anchor="middle">{html.escape(label)}</text>')
    out.append("</svg>")
    return "".join(out)


def hbars(rows: list[tuple[str, float, str]], width: int = 640, label_w: int = 128,
          value_fmt: str = "{:+.2f}pp", max_label: int = 12) -> str:
    row_h = 26
    top = 14
    height = top + row_h * len(rows) + 12
    plot_w = width - label_w - 96
    peak = max(abs(value) for _, value, _ in rows) or 1
    out = [f'<svg viewBox="0 0 {width} {height}" width="100%" role="img">']
    for index, (label, value, note) in enumerate(rows):
        y = top + row_h * index
        bar_w = plot_w * abs(value) / peak
        color = ORANGE if value > 0 else "#9ca3af"
        clipped = label if len(label) <= max_label else label[: max_label - 1] + "…"
        out.append(f'<text x="{label_w - 6}" y="{y + 15}" font-size="11" fill="#111827" text-anchor="end">{html.escape(clipped)}</text>')
        out.append(f'<rect x="{label_w}" y="{y + 5}" width="{max(bar_w, 1):.1f}" height="14" fill="{color}" rx="2" opacity="0.85"/>')
        out.append(f'<text x="{label_w + bar_w + 6:.1f}" y="{y + 15}" font-size="10" fill="#374151">{value_fmt.format(value)} {html.escape(note)}</text>')
    out.append("</svg>")
    return "".join(out)


def table(headers: list[str], rows: list[list[str]], classes: dict[int, str] | None = None) -> str:
    out = ['<table>', "<thead><tr>"]
    for header in headers:
        out.append(f"<th>{html.escape(header)}</th>")
    out.append("</tr></thead><tbody>")
    for row in rows:
        out.append("<tr>")
        for index, cell in enumerate(row):
            klass = f' class="{classes[index]}"' if classes and index in classes else ""
            out.append(f"<td{klass}>{cell}</td>")
        out.append("</tr>")
    out.append("</tbody></table>")
    return "".join(out)


def kpi(label: str, value: str, note: str = "") -> str:
    return (
        '<div class="kpi"><div class="kpi-label">' + html.escape(label) + "</div>"
        '<div class="kpi-value">' + value + "</div>"
        '<div class="kpi-note">' + note + "</div></div>"
    )


def main() -> None:
    overview = {row["split"]: row for row in read("overview.csv")}
    strata = [row for row in read("length_strata.csv") if row["split"] == "train"]
    order = ["01-10", "11-20", "21-30", "31-40", "41-60", "61-100", "100+"]
    strata.sort(key=lambda row: order.index(row["length_stratum"]))

    categories = [row for row in read("category_metrics.csv") if row["split"] == "train"]
    categories.sort(key=lambda row: int(row["exposures"]), reverse=True)
    residuals = read("category_residuals.csv")[:10]
    intents = [row for row in read("intent_metrics.csv") if row["split"] == "train"]
    intent_res = read("intent_residuals.csv")
    opportunities = read("opportunities_top30.csv")
    relative = [row for row in read("relative_time_metrics.csv") if row["split"] == "train"]

    train = overview["train"]
    test = overview["test"]
    exposures_train = int(train["exposures"])
    long_share = (
        sum(int(row["exposures"]) for row in strata if row["length_stratum"] == "100+")
        / exposures_train
    )

    cards = "".join(
        [
            kpi("搜索请求", fmt_int(train["requests"]), f"测试段 {fmt_int(test['requests'])}"),
            kpi("商品曝光", fmt_int(train["exposures"]), f"测试段 {fmt_int(test['exposures'])}"),
            kpi("商品点击率", fmt_pct(train["item_ctr"]), f"测试段 {fmt_pct(test['item_ctr'])}"),
            kpi("请求点击率", fmt_pct(train["request_click_rate"]), f"测试段 {fmt_pct(test['request_click_rate'])}"),
            kpi("100+ 条曝光占比", fmt_pct(long_share, 1), "仅 6.9% 的请求"),
            kpi("机会候选词", f"{len(opportunities)}", "Top 30 已导出"),
        ]
    )

    page1 = f"""
    <section id="page1" class="page">
      <h2>1 · 总览</h2>
      <p class="lede">曝光高度集中在长列表：少部分请求贡献了大部分曝光，也拉低了单件点击率。</p>
      <div class="kpis">{cards}</div>
      <div class="split">
        <div class="card">
          <h3>训练段 vs 测试段（时间外）</h3>
          {table(
              ["指标", "训练段", "测试段"],
              [
                  ["请求数", fmt_int(train["requests"]), fmt_int(test["requests"])],
                  ["去重用户", fmt_int(train["users"]), fmt_int(test["users"])],
                  ["商品曝光", fmt_int(train["exposures"]), fmt_int(test["exposures"])],
                  ["商品点击率", fmt_pct(train["item_ctr"]), fmt_pct(test["item_ctr"])],
                  ["请求点击率", fmt_pct(train["request_click_rate"]), fmt_pct(test["request_click_rate"])],
                  ["购买请求率", fmt_pct(train["request_purchase_rate"]), fmt_pct(test["request_purchase_rate"])],
                  ["平均展示条数", f"{float(train['avg_list_length']):.1f}", f"{float(test['avg_list_length']):.1f}"],
              ],
          )}
        </div>
        <div class="card">
          <h3>曝光结构</h3>
          {vbars([(row["length_stratum"], int(row["exposures"]) / exposures_train * 100)
                  for row in strata], value_fmt="{:.1f}%", color="#7c9ef0", y_label="各条数段占总曝光比例")}
          <p class="note">7 个条数段中，100+ 段单独占四成曝光。</p>
        </div>
      </div>
    </section>
    """

    page2 = f"""
    <section id="page2" class="page">
      <h2>2 · 条数效率（核心）</h2>
      <p class="lede">同一批用户：展示 1–10 条时单件点击率 8.96%，100+ 条时只有 2.19%；但请求点击率从 36.6% 升到 84.1%。</p>
      <div class="split">
        <div class="card">
          <h3>商品点击率（点击商品 / 曝光商品）</h3>
          {vbars([(row["length_stratum"], float(row["item_ctr"]) * 100) for row in strata], y_label="训练段")}
        </div>
        <div class="card">
          <h3>请求点击率（有点击的请求 / 请求）</h3>
          {vbars([(row["length_stratum"], float(row["request_click_rate"]) * 100) for row in strata],
                 color="#3aa981", y_label="训练段")}
        </div>
      </div>
      <div class="card wide">
        <h3>按条数段明细</h3>
        {table(
            ["条数段", "请求数", "曝光数", "商品点击率", "请求点击率"],
            [[row["length_stratum"], fmt_int(row["requests"]), fmt_int(row["exposures"]),
              fmt_pct(row["item_ctr"]), fmt_pct(row["request_click_rate"])] for row in strata],
        )}
      </div>
    </section>
    """

    page3 = f"""
    <section id="page3" class="page">
      <h2>3 · 类目效率</h2>
      <p class="lede">按同条数基准校准后，女装的每曝光差距从 0.78pp 收窄到 0.25pp；男鞋的差距反而最大。</p>
      <div class="split">
        <div class="card">
          <h3>曝光量 Top 10 类目</h3>
          {table(
              ["类目", "曝光", "点击率"],
              [[html.escape(row["category"]), fmt_int(row["exposures"]), fmt_pct(row["item_ctr"])] for row in categories[:10]],
          )}
        </div>
        <div class="card">
          <h3>同条数校准后的缺口（百分点 / 缺口点击）</h3>
          {hbars([(row["category"], float(row["gap_pp"]), f"({fmt_int(row['gap_clicks'])})") for row in residuals])}
          <p class="note">橙色为实际低于期望；灰色为高于期望。</p>
        </div>
      </div>
    </section>
    """

    intent_share_total = sum(int(row["requests"]) for row in intents)
    page4 = f"""
    <section id="page4" class="page">
      <h2>4 · 需求结构</h2>
      <p class="lede">规则标签只用于结构描述：按同条数校准后，各标签的效率差异都在 ±0.2pp 内，品牌/店铺词甚至略好于期望。</p>
      <div class="split">
        <div class="card">
          <h3>请求占比（训练段）</h3>
          {table(
              ["需求标签", "请求数", "占比", "平均条数", "商品点击率"],
              [[html.escape(row["intent"]), fmt_int(row["requests"]),
                f"{int(row['requests']) / intent_share_total * 100:.1f}%",
                f"{float(row['avg_list_length']):.1f}", fmt_pct(row["item_ctr"])] for row in intents],
          )}
        </div>
        <div class="card">
          <h3>同条数校准后的差距</h3>
          {hbars([(row["intent"], float(row["gap_pp"]), f"({fmt_int(row['gap_clicks'])})") for row in intent_res],
                 label_w=150, max_label=14, value_fmt="{:+.2f}pp")}
          <p class="note">负值表示实际好于同条数期望。</p>
        </div>
      </div>
    </section>
    """

    page5 = f"""
    <section id="page5" class="page">
      <h2>5 · 机会清单</h2>
      <p class="lede">Top 30 合计 64.6 万曝光，实际 14,828 次点击，同条数期望 21,244 次，缺口约 6,400 次（≈1.0% 曝光）。</p>
      <div class="card wide scroll">
        {table(
            ["#", "搜索词", "请求", "曝光", "实际 CTR", "期望 CTR", "差距", "缺口点击", "请求点击率", "测试段"],
            [[row["rank"], html.escape(row["query"]), fmt_int(row["requests"]), fmt_int(row["exposures"]),
              fmt_pct(row["item_ctr"]), fmt_pct(row["expected_ctr"]),
              f'<span class="chip">{float(row["gap_pp"]):.2f}pp</span>',
              fmt_int(row["gap_clicks"]), fmt_pct(row["request_click_rate"]),
              html.escape(row["validation"])] for row in opportunities],
            classes={6: "num", 7: "num"},
        )}
      </div>
    </section>
    """

    relative_rows = "".join(
        f'<tr><td>{row["time_bucket"]}</td><td>{fmt_int(row["requests"])}</td>'
        f'<td>{fmt_pct(row["item_ctr"])}</td><td>{fmt_pct(row["request_click_rate"])}</td></tr>'
        for row in relative
    )

    document = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>快手电商搜索需求与转化效率诊断 · 看板预览</title>
<style>
  :root {{ --blue:{BLUE}; --orange:{ORANGE}; --grey:{GREY}; --grid:{GRID}; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; font-family:{FONT}; color:#111827; background:#f6f7f9; }}
  header {{ padding:22px 28px 10px; }}
  header h1 {{ margin:0 0 6px; font-size:22px; }}
  header p {{ margin:0; color:var(--grey); font-size:13px; }}
  nav {{ display:flex; gap:8px; padding:14px 28px; flex-wrap:wrap; }}
  nav a {{ text-decoration:none; font-size:13px; padding:7px 14px; border-radius:999px; background:#fff;
           border:1px solid #d9dde5; color:#374151; }}
  nav a:hover {{ border-color:var(--blue); color:var(--blue); }}
  main {{ padding:0 28px 40px; }}
  .page {{ background:#fff; border:1px solid #e3e6ec; border-radius:12px; padding:20px 22px; margin-bottom:18px; }}
  .page h2 {{ margin:0 0 6px; font-size:17px; }}
  .lede {{ margin:0 0 14px; color:var(--grey); font-size:13px; }}
  .kpis {{ display:grid; grid-template-columns:repeat(6, 1fr); gap:10px; margin-bottom:16px; }}
  .kpi {{ border:1px solid #e3e6ec; border-radius:10px; padding:10px 12px; background:#fbfcfe; }}
  .kpi-label {{ font-size:11px; color:var(--grey); }}
  .kpi-value {{ font-size:19px; font-weight:600; margin:2px 0; }}
  .kpi-note {{ font-size:10px; color:#9ca3af; }}
  .split {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }}
  .card {{ border:1px solid #eceff3; border-radius:10px; padding:12px 14px; }}
  .card.wide {{ margin-top:14px; }}
  .card h3 {{ margin:0 0 8px; font-size:13px; color:#374151; font-weight:600; }}
  .card .note {{ margin:6px 0 0; font-size:11px; color:#9ca3af; }}
  table {{ width:100%; border-collapse:collapse; font-size:12px; }}
  th, td {{ text-align:left; padding:6px 8px; border-bottom:1px solid #f0f2f5; }}
  th {{ background:#f8fafc; color:#4b5563; font-weight:600; }}
  td.num, th.num {{ text-align:right; }}
  .chip {{ display:inline-block; padding:1px 7px; border-radius:999px; background:#fdece3; color:#b4450f; font-size:11px; }}
  .scroll {{ max-height:460px; overflow:auto; }}
  footer {{ padding:0 28px 30px; color:#9ca3af; font-size:11px; }}
</style>
</head>
<body>
<header>
  <h1>快手电商搜索需求与转化效率诊断</h1>
  <p>555,553 次搜索 · 17,800,904 次曝光 · 102,086 名用户｜静态预览版（正式看板用 Power BI，见 docs/powerbi.md）</p>
</header>
<nav>
  <a href="#page1">总览</a><a href="#page2">条数效率</a><a href="#page3">类目效率</a>
  <a href="#page4">需求结构</a><a href="#page5">机会清单</a>
</nav>
<main>
{page1}
{page2}
{page3}
{page4}
{page5}
<section class="page">
  <h2>附 · 相对时间（不可还原为日期）</h2>
  <p class="lede">20 个等宽区间，只用于看量级波动，不能当作星期/小时趋势。</p>
  <div class="card wide">
    <table><thead><tr><th>相对区间</th><th>请求数</th><th>商品点击率</th><th>请求点击率</th></tr></thead>
    <tbody>{relative_rows}</tbody></table>
  </div>
</section>
</main>
<footer>
  口径：商品点击率 = 点击商品/曝光商品；请求点击率 = 有点击的请求/请求；期望点击 = Σ(条数段曝光 × 该段训练基准 CTR)。
  数据为公开聚合结果，不含用户级明细。完整口径见 docs/metrics.md。
</footer>
</body>
</html>
"""
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(document, encoding="utf-8")
    print(f"wrote {TARGET.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
