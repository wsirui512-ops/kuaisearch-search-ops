"""Render the three headline charts as dependency-free SVG files.

These SVGs only feed the README so a reader sees the key evidence without opening
the dashboard deck.
"""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "outputs_public"
IMAGES = ROOT / "docs" / "images"

FONT = "'Segoe UI', 'Microsoft YaHei', 'PingFang SC', sans-serif"
BAR = "#2f6fdd"
ACCENT = "#e8590c"
GREY = "#6b7280"
GRID = "#e5e7eb"


def read_csv(name: str) -> list[dict[str, str]]:
    with (PUBLIC / name).open(encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def svg_open(width: int, height: int, title: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="{FONT}">',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        f'<text x="24" y="34" font-size="18" font-weight="600" fill="#111827">{title}</text>',
    ]


def vertical_bars(
    rows: list[tuple[str, float]],
    title: str,
    subtitle: str,
    file_name: str,
    value_format: str = "{:.2f}%",
) -> None:
    width, height = 760, 420
    left, right, top, bottom = 70, 30, 70, 90
    plot_w = width - left - right
    plot_h = height - top - bottom
    peak = max(value for _, value in rows) * 1.15
    parts = svg_open(width, height, title)
    parts.append(f'<text x="24" y="56" font-size="12" fill="{GREY}">{subtitle}</text>')
    for step in range(5):
        value = peak * step / 4
        y = top + plot_h - plot_h * step / 4
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width - right}" y2="{y:.1f}" stroke="{GRID}"/>')
        parts.append(
            f'<text x="{left - 10}" y="{y + 4:.1f}" font-size="11" fill="{GREY}" '
            f'text-anchor="end">{value:.1f}%</text>'
        )
    slot = plot_w / len(rows)
    bar_w = slot * 0.55
    for index, (label, value) in enumerate(rows):
        bar_h = plot_h * value / peak
        x = left + slot * index + (slot - bar_w) / 2
        y = top + plot_h - bar_h
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" fill="{BAR}" rx="3"/>')
        parts.append(
            f'<text x="{x + bar_w / 2:.1f}" y="{y - 8:.1f}" font-size="11" fill="#111827" '
            f'text-anchor="middle">{value_format.format(value)}</text>'
        )
        parts.append(
            f'<text x="{x + bar_w / 2:.1f}" y="{top + plot_h + 22}" font-size="11" fill="{GREY}" '
            f'text-anchor="middle">{label}</text>'
        )
    parts.append("</svg>")
    (IMAGES / file_name).write_text("\n".join(parts), encoding="utf-8")


def horizontal_bars(
    rows: list[tuple[str, float, str]],
    title: str,
    subtitle: str,
    file_name: str,
    value_format: str = "{:+.2f}pp",
    width: int = 760,
    label_width: int = 150,
    max_label: int = 12,
) -> None:
    row_h = 34
    top = 84
    height = top + row_h * len(rows) + 40
    plot_w = width - label_width - 110
    peak = max(abs(value) for _, value, _ in rows) * 1.05
    parts = svg_open(width, height, title)
    parts.append(f'<text x="24" y="56" font-size="12" fill="{GREY}">{subtitle}</text>')
    for index, (label, value, note) in enumerate(rows):
        y = top + row_h * index
        bar_w = plot_w * abs(value) / peak
        color = ACCENT if value > 0 else GREY
        if len(label) > max_label:
            label = label[: max_label - 1] + "…"
        parts.append(
            f'<text x="{label_width - 10}" y="{y + 20}" font-size="12" fill="#111827" '
            f'text-anchor="end">{label}</text>'
        )
        parts.append(
            f'<rect x="{label_width}" y="{y + 6}" width="{bar_w:.1f}" height="20" fill="{color}" rx="3" opacity="0.85"/>'
        )
        parts.append(
            f'<text x="{label_width + bar_w + 8:.1f}" y="{y + 20}" font-size="11" fill="#111827">'
            f'{value_format.format(value)} {note}</text>'
        )
    parts.append("</svg>")
    (IMAGES / file_name).write_text("\n".join(parts), encoding="utf-8")


def main() -> None:
    IMAGES.mkdir(parents=True, exist_ok=True)

    strata = [row for row in read_csv("length_strata.csv") if row["split"] == "train"]
    order = ["01-10", "11-20", "21-30", "31-40", "41-60", "61-100", "100+"]
    strata.sort(key=lambda row: order.index(row["length_stratum"]))
    vertical_bars(
        [(row["length_stratum"], float(row["item_ctr"]) * 100) for row in strata],
        "结果条数越长，单件商品越难被点",
        "训练段：每次请求展示条数 × 商品点击率（点击商品 / 曝光商品）",
        "chart_length_ctr.svg",
    )

    top = read_csv("opportunities_top30.csv")[:10]
    horizontal_bars(
        [(row["query"], float(row["gap_pp"]), f"({float(row['gap_clicks']):.0f} 次)") for row in top],
        "同条数基准下点击缺口最大的 10 个搜索词",
        "训练段：实际商品点击率低于同条数期望的百分点（括号内为描述性缺口点击）",
        "chart_top_gap.svg",
        label_width=170,
    )

    categories = read_csv("category_residuals.csv")[:8]
    horizontal_bars(
        [(row["category"], float(row["gap_pp"]), f"({float(row['gap_clicks']):.0f} 次)") for row in categories],
        "一级类目：按曝光结构校准后的点击缺口",
        "训练段：实际商品点击率与同条数期望之差（百分点）",
        "chart_category_gap.svg",
        label_width=190,
    )
    print("wrote", ", ".join(sorted(path.name for path in IMAGES.glob("*.svg"))))


if __name__ == "__main__":
    main()
