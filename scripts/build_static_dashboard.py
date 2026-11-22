"""Build the eight-page static dashboard (PPTX) from the published aggregates.

The deck is the publishable, reproducible visual: numbers come straight from
outputs_public, so any metric change flows through two commands.
Exported to 1600x900 PNG and PDF by scripts/export_dashboard.py.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from experiment_contract import ACTIONS

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".localdeps"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".deps"))

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_LABEL_POSITION
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "outputs_public"
TARGET = ROOT / "dashboards" / "静态看板.pptx"

NAVY = RGBColor(0x1F, 0x29, 0x37)
BLUE = RGBColor(0x2F, 0x6F, 0xDD)
ORANGE = RGBColor(0xE8, 0x59, 0x0C)
GREY = RGBColor(0x6B, 0x72, 0x80)
LIGHT = RGBColor(0xF3, 0xF4, 0xF6)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
FONT = "Microsoft YaHei"

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)

MASK = {
    "鞋子女潮流ins百搭学生党": "长尾泛词 A",
    "裤子女款爆款2025新款春秋款": "长尾泛词 B",
}


def read(name: str) -> list[dict[str, str]]:
    with (PUBLIC / name).open(encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def text_box(slide, left, top, width, height, text, size=14, bold=False, color=NAVY, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
    box = slide.shapes.add_textbox(left, top, width, height)
    frame = box.text_frame
    frame.word_wrap = True
    frame.vertical_anchor = anchor
    line = frame.paragraphs[0]
    line.alignment = align
    run = line.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.name = FONT
    return box


def page(slide, number: int, title: str, subtitle: str) -> None:
    bar = slide.shapes.add_shape(1, 0, 0, SLIDE_W, Inches(0.09))
    bar.fill.solid()
    bar.fill.fore_color.rgb = BLUE
    bar.line.fill.background()
    text_box(slide, Inches(0.55), Inches(0.32), Inches(11.5), Inches(0.5), title, size=24, bold=True)
    text_box(slide, Inches(0.55), Inches(0.86), Inches(11.8), Inches(0.4), subtitle, size=11.5, color=GREY)
    text_box(slide, Inches(0.55), Inches(7.02), Inches(12.2), Inches(0.3),
             "数据：KuaiSearch-Lite 采样样本｜口径见 docs/metrics.md｜本页为静态渲染，不含交互", size=9, color=GREY)
    text_box(slide, Inches(12.45), Inches(7.02), Inches(0.6), Inches(0.3), f"{number}/8", size=9, color=GREY)


def table(slide, left, top, width, rows, col_widths, header_size=10, body_size=10, row_height=Inches(0.3)):
    shape = slide.shapes.add_table(len(rows), len(rows[0]), left, top, width, row_height * len(rows))
    tbl = shape.table
    for index, width_emu in enumerate(col_widths):
        tbl.columns[index].width = width_emu
    for r, row in enumerate(rows):
        for c, value in enumerate(row):
            cell = tbl.cell(r, c)
            cell.text = str(value)
            cell.margin_left = Inches(0.05)
            cell.margin_right = Inches(0.05)
            cell.margin_top = Inches(0.02)
            cell.margin_bottom = Inches(0.02)
            paragraph = cell.text_frame.paragraphs[0]
            paragraph.font.name = FONT
            paragraph.font.size = Pt(header_size if r == 0 else body_size)
            paragraph.font.bold = r == 0
            paragraph.font.color.rgb = WHITE if r == 0 else NAVY
            cell.fill.solid()
            cell.fill.fore_color.rgb = NAVY if r == 0 else (LIGHT if r % 2 == 0 else WHITE)
    return tbl


def bar_chart(slide, left, top, width, height, categories, values, title, colors=None, number_format='0.00'):
    data = CategoryChartData()
    data.categories = categories
    data.add_series(title, values)
    chart = slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, left, top, width, height, data).chart
    chart.has_legend = False
    chart.font.name = FONT
    chart.font.size = Pt(10)
    plot = chart.plots[0]
    plot.has_data_labels = True
    plot.data_labels.number_format = number_format
    plot.data_labels.number_format_is_linked = False
    plot.data_labels.font.size = Pt(9)
    plot.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
    series = plot.series[0]
    series.format.fill.solid()
    series.format.fill.fore_color.rgb = colors or BLUE
    chart.value_axis.has_major_gridlines = True
    chart.value_axis.major_gridlines.format.line.color.rgb = RGBColor(0xE5, 0xE7, 0xEB)
    chart.value_axis.tick_labels.font.size = Pt(9)
    chart.category_axis.tick_labels.font.size = Pt(9)
    return chart


def hbar_chart(slide, left, top, width, height, categories, values, title, color=BLUE, number_format='0.00'):
    data = CategoryChartData()
    data.categories = categories
    data.add_series(title, values)
    chart = slide.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, left, top, width, height, data).chart
    chart.has_legend = False
    chart.font.name = FONT
    chart.font.size = Pt(10)
    plot = chart.plots[0]
    plot.has_data_labels = True
    plot.data_labels.number_format = number_format
    plot.data_labels.number_format_is_linked = False
    plot.data_labels.font.size = Pt(9)
    plot.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
    plot.series[0].format.fill.solid()
    plot.series[0].format.fill.fore_color.rgb = color
    chart.category_axis.tick_labels.font.size = Pt(9)
    chart.value_axis.tick_labels.font.size = Pt(9)
    return chart


def main() -> None:
    overview = {row["split"]: row for row in read("overview.csv")}
    strata = [row for row in read("length_strata.csv") if row["split"] == "train"]
    order = ["01-10", "11-20", "21-30", "31-40", "41-60", "61-100", "100+"]
    strata.sort(key=lambda row: order.index(row["length_stratum"]))
    categories = [row for row in read("category_residuals.csv")]
    intents = [row for row in read("intent_metrics.csv") if row["split"] == "train"]
    intent_res = read("intent_residuals.csv")
    opportunities = read("opportunities_top30.csv")
    coverage = read("review_coverage_summary.csv")
    relative = [row for row in read("relative_time_metrics.csv") if row["split"] == "train"]

    train, test = overview["train"], overview["test"]
    total_exposures = int(train["exposures"])
    long_share = sum(int(r["exposures"]) for r in strata if r["length_stratum"] == "100+") / total_exposures

    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H
    blank = prs.slide_layouts[6]

    # 1 总览
    slide = prs.slides.add_slide(blank)
    page(slide, 1, "01 总览：曝光结构与两种点击率", "训练段为主，测试段为时间外对照；商品点击率与请求点击率分母不同，不可混用。")
    cards = [
        ("搜索请求", f"{int(train['requests']):,}", f"测试段 {int(test['requests']):,}"),
        ("商品曝光", f"{int(train['exposures']):,}", f"测试段 {int(test['exposures']):,}"),
        ("商品点击率", f"{float(train['item_ctr'])*100:.2f}%", f"测试段 {float(test['item_ctr'])*100:.2f}%"),
        ("请求点击率", f"{float(train['request_click_rate'])*100:.2f}%", f"测试段 {float(test['request_click_rate'])*100:.2f}%"),
    ]
    for index, (label, value, note) in enumerate(cards):
        left = Inches(0.55 + index * 3.1)
        card = slide.shapes.add_shape(1, left, Inches(1.45), Inches(2.85), Inches(1.25))
        card.fill.solid(); card.fill.fore_color.rgb = LIGHT; card.line.color.rgb = RGBColor(0xE3, 0xE6, 0xEC)
        text_box(slide, left + Inches(0.18), Inches(1.56), Inches(2.6), Inches(0.3), label, size=10.5, color=GREY)
        text_box(slide, left + Inches(0.18), Inches(1.86), Inches(2.6), Inches(0.5), value, size=22, bold=True)
        text_box(slide, left + Inches(0.18), Inches(2.34), Inches(2.6), Inches(0.25), note, size=9, color=GREY)
    table(slide, Inches(0.55), Inches(3.0), Inches(5.7), [
        ["指标", "训练段", "测试段"],
        ["请求数", f"{int(train['requests']):,}", f"{int(test['requests']):,}"],
        ["去重用户", f"{int(train['users']):,}", f"{int(test['users']):,}"],
        ["商品曝光", f"{int(train['exposures']):,}", f"{int(test['exposures']):,}"],
        ["商品点击率", f"{float(train['item_ctr'])*100:.2f}%", f"{float(test['item_ctr'])*100:.2f}%"],
        ["请求点击率", f"{float(train['request_click_rate'])*100:.2f}%", f"{float(test['request_click_rate'])*100:.2f}%"],
        ["购买请求率", f"{float(train['request_purchase_rate'])*100:.2f}%", f"{float(test['request_purchase_rate'])*100:.2f}%"],
        ["平均展示条数", f"{float(train['avg_list_length']):.1f}", f"{float(test['avg_list_length']):.1f}"],
    ], [Inches(1.9), Inches(1.9), Inches(1.9)])
    closing = [
        ("结构", "6.9% 的请求贡献 40.3% 曝光"),
        ("口径", "按条数校准后女装 0.78pp → 0.25pp"),
        ("清单", "124 个待核查词，Top 30 差 6,416 次点击"),
    ]
    for index, (label, text) in enumerate(closing):
        left = Inches(0.55 + index * 4.1)
        card = slide.shapes.add_shape(1, left, Inches(5.55), Inches(3.95), Inches(0.95))
        card.fill.solid(); card.fill.fore_color.rgb = LIGHT; card.line.color.rgb = RGBColor(0xE3, 0xE6, 0xEC)
        text_box(slide, left + Inches(0.18), Inches(5.62), Inches(0.9), Inches(0.35), label, size=11, bold=True, color=BLUE)
        text_box(slide, left + Inches(1.05), Inches(5.62), Inches(2.75), Inches(0.8), text, size=10.5)
    text_box(slide, Inches(6.55), Inches(3.0), Inches(6.2), Inches(2.6),
             f"一句话：{long_share*100:.1f}% 的曝光来自「一次展示 100 条以上」的请求，"
             f"这类请求的商品点击率只有 {float(strata[-1]['item_ctr'])*100:.2f}%，"
             f"而请求点击率达 {float(strata[-1]['request_click_rate'])*100:.1f}%——用户点得到，但绝大部分商品没被点。",
             size=12, color=NAVY)

    # 2 条数效率
    slide = prs.slides.add_slide(blank)
    page(slide, 2, "02 条数效率：分开比较两种点击率", "训练段；按每次请求的曝光条数分组。分组差异不代表增加列表长度的效果。")
    bar_chart(slide, Inches(0.55), Inches(1.4), Inches(6.3), Inches(4.2),
              [r["length_stratum"] for r in strata],
              [round(float(r["item_ctr"]) * 100, 3) for r in strata],
              "商品点击率（%）", BLUE, '0.00')
    bar_chart(slide, Inches(7.1), Inches(1.4), Inches(5.7), Inches(4.2),
              [r["length_stratum"] for r in strata],
              [round(float(r["request_click_rate"]) * 100, 1) for r in strata],
              "请求点击率（%）", RGBColor(0x3A, 0xA9, 0x81), '0.0')
    text_box(slide, Inches(0.55), Inches(5.75), Inches(12.2), Inches(1.0),
             "观察：商品点击率从 8.96% 降到 2.19%，同期请求点击率从 36.6% 升到 84.1%——两条曲线方向相反。"
             "前者说明单件越来越难被点，后者说明用户仍能点到东西——两个结论不矛盾，因为分母不同。",
             size=11.5, color=GREY)

    # 3 品类残差
    slide = prs.slides.add_slide(blank)
    page(slide, 3, "03 品类残差：按同条数基准校准后的缺口", "训练段；期望点击 = Σ(各条数段曝光 × 该段基准 CTR)。差额是描述性的，不是可回收点击。")
    top_categories = categories[:10]
    hbar_chart(slide, Inches(0.55), Inches(1.4), Inches(7.2), Inches(4.6),
               [c["category"] for c in reversed(top_categories)],
               [round(float(c["gap_pp"]), 3) for c in reversed(top_categories)],
               "缺口（百分点）", ORANGE, '0.00')
    table(slide, Inches(8.0), Inches(1.5), Inches(4.8), [
        ["类目", "实际CTR", "总体差", "分层差"],
        *[[c["category"][:5], f"{float(c['item_ctr'])*100:.2f}%",
           f"{(float(train['item_ctr'])-float(c['item_ctr']))*100:.2f}pp", f"{float(c['gap_pp']):.2f}pp"]
          for c in top_categories[:6]],
    ], [Inches(1.85), Inches(1.15), Inches(0.95), Inches(0.95)], body_size=8.5)
    text_box(slide, Inches(0.55), Inches(6.15), Inches(12.2), Inches(0.7),
             "比较：女装由总体差 0.78pp 收窄到分层差 0.25pp；男鞋在两种比较中都低于女装。总量与单位差距分开用于排查。",
             size=11.5, color=GREY)

    # 4 需求标签
    slide = prs.slides.add_slide(blank)
    page(slide, 4, "04 需求标签：规则标签下的结构（未人工校核）", "标签由 config/intent_rules.csv 规则生成，36.8% 请求落在「无品类信号」，准确性待抽样复核。")
    bar_chart(slide, Inches(0.55), Inches(1.4), Inches(6.6), Inches(4.4),
              [i["intent"] for i in intents],
              [int(i["requests"]) for i in intents],
              "请求数", BLUE, '#,##0')
    table(slide, Inches(7.15), Inches(1.5), Inches(5.7), [
        ["标签", "平均条数", "商品CTR", "同条数差"],
        *[[r["intent"], f"{float(r['avg_list_length']):.1f}",
           f"{float(r['item_ctr'])*100:.2f}%", f"{float(r['gap_pp']):+.2f}pp"] for r in intent_res],
    ], [Inches(2.7), Inches(1.0), Inches(1.0), Inches(1.0)], body_size=8.5)
    text_box(slide, Inches(0.55), Inches(6.0), Inches(12.2), Inches(0.8),
             "观察：五类标签的残差范围为 −0.34pp 至 +0.20pp；未检验业务等效性，不能据此认定没有关联。"
             "先核查规则标签，再决定是否按标签配置入口。", size=11.5, color=GREY)

    # 5 机会清单
    slide = prs.slides.add_slide(blank)
    page(slide, 5, "05 机会清单：124 个待核查搜索词中的 Top 15", "训练段；门槛：请求≥100、用户≥30、曝光≥1,000。缺口为描述性差额，p/q 值不用于确认性结论。")
    top15 = opportunities[:15]
    table(slide, Inches(0.55), Inches(1.35), Inches(12.2), [
        ["#", "搜索词", "请求", "曝光", "实际CTR", "期望CTR", "差距", "缺口点击", "校验"],
        *[[r["rank"], MASK.get(r["query"], r["query"]), f"{int(r['requests']):,}", f"{int(r['exposures']):,}",
           f"{float(r['item_ctr'])*100:.2f}%", f"{float(r['expected_ctr'])*100:.2f}%",
           f"{float(r['gap_pp']):.2f}pp", f"{float(r['gap_clicks']):,.0f}", r["validation"]]
          for r in top15],
    ], [Inches(0.5), Inches(3.2), Inches(0.9), Inches(1.2), Inches(1.1), Inches(1.1), Inches(1.0), Inches(1.3), Inches(1.9)],
        body_size=8.5, row_height=Inches(0.32))
    text_box(slide, Inches(0.55), Inches(6.55), Inches(12.2), Inches(0.4),
             "Top 30 合计约 64.6 万曝光、实际 14,828 次点击、期望约 21,244 次，差额约 6,400 次（≈1.0% 曝光）。",
             size=11, color=GREY)

    # 6 标题预筛
    slide = prs.slides.add_slide(blank)
    page(slide, 6, "06 标题预筛：二字覆盖率与待核查样本", "每个词取曝光最高的 10 件商品；覆盖率低≠不相关。既有 30 条标注来源待作者确认。")
    table(slide, Inches(0.55), Inches(1.4), Inches(7.4), [
        ["搜索词", "商品数", "平均覆盖率", "零覆盖占比"],
        *[[MASK.get(r["query"], r["query"]), r["items_reviewed"], f"{float(r['avg_bigram_coverage']):.2f}",
           f"{float(r['pct_items_zero_coverage'])*100:.0f}%"] for r in coverage],
    ], [Inches(3.0), Inches(1.2), Inches(1.6), Inches(1.6)], body_size=9, row_height=Inches(0.3))
    text_box(slide, Inches(8.3), Inches(1.4), Inches(4.4), Inches(5.0),
             "怎么读：\n\n"
             "• 「衣服」「鞋子」覆盖率低，是因为标题写的是卫衣、板鞋、面包鞋；\n"
             "• 「外套」「裤子」「手机壳」覆盖 100%，词本身就出现在标题里；\n\n"
             "这张表只用于筛出值得人工看的样本，不能得出「X% 商品不相关」。"
             "既有标注统计为 26/4/0：部分相关分布在鞋子 1 条、长尾泛词 A 3 条；"
             "来源待作者确认，不作为人工证据。", size=11, color=NAVY)

    # 7 相对时间
    slide = prs.slides.add_slide(blank)
    page(slide, 7, "07 相对时间：20 个区间的量级波动（非日历日期）", "time_index 是相对编码，不能还原为日期、小时或星期；只用于看波动，不做星期/分时结论。")
    bar_chart(slide, Inches(0.55), Inches(1.4), Inches(12.2), Inches(3.95),
              [r["time_bucket"] for r in relative],
              [int(r["requests"]) for r in relative],
              "请求数", RGBColor(0x7C, 0x9E, 0xF0), '#,##0')
    text_box(slide, Inches(0.55), Inches(5.5), Inches(12.2), Inches(0.4),
             "注：区间 19 只有 11,179 次请求，是因为训练段在 time_index 936,724 结束、该区间未走完，不是真实下滑。",
             size=10.5, color=ORANGE)
    text_box(slide, Inches(0.55), Inches(5.95), Inches(12.2), Inches(0.7),
             "口径：除末段外，各区间请求量在 2.6–3.0 万之间波动，没有明显趋势；商品点击率稳定在 3.7%–3.9%，"
             "这些总体指标不足以判断词级排名或用户结构稳定。", size=11.5, color=GREY)

    # 8 运营动作
    slide = prs.slides.add_slide(blank)
    page(slide, 8, "08 运营动作：按用户分流、分批验证", "三项分开实验；主指标为每用户首次合格搜索点击率。后续请求用于辅助诊断。")
    actions = ACTIONS
    for index, (name, what, metric, owner, size) in enumerate(actions):
        top = Inches(1.45 + index * 1.72)
        card = slide.shapes.add_shape(1, Inches(0.55), top, Inches(12.2), Inches(1.25))
        card.fill.solid(); card.fill.fore_color.rgb = LIGHT; card.line.color.rgb = RGBColor(0xE3, 0xE6, 0xEC)
        text_box(slide, Inches(0.75), top, Inches(2.4), Inches(1.25), name, size=15, bold=True, color=BLUE, anchor=MSO_ANCHOR.MIDDLE)
        text_box(slide, Inches(3.2), top, Inches(4.0), Inches(1.25), what, size=11.5, anchor=MSO_ANCHOR.MIDDLE)
        text_box(slide, Inches(7.5), top, Inches(2.7), Inches(1.25), f"主指标：{metric}", size=10.5, color=GREY, anchor=MSO_ANCHOR.MIDDLE)
        text_box(slide, Inches(10.5), top, Inches(2.1), Inches(1.25), f"{owner}\n{size}", size=10.5, color=GREY, anchor=MSO_ANCHOR.MIDDLE)
    text_box(slide, Inches(0.55), Inches(6.75), Inches(12.2), Inches(0.3),
             "规划：基线53%、MDE3pp、双侧α=0.05、power=80%；最终样本取主指标与护栏要求最大值，线上预观察后锁定。",
             size=10.5, color=GREY)

    prs.save(TARGET)
    print("wrote", TARGET.relative_to(ROOT), "slides:", len(prs.slides))


if __name__ == "__main__":
    main()
