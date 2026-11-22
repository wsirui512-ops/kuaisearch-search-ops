"""Check dashboard exports before publishing: page count, sizes, blank pages, app chrome.

Run after building/exporting the dashboard:
    python scripts/check_dashboard_assets.py

Exit code 1 means the assets are not publishable yet.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from PIL import Image, ImageStat

ROOT = Path(__file__).resolve().parents[1]
IMAGES = ROOT / "dashboards" / "images"
PDF = ROOT / "dashboards" / "看板.pdf"
EXPECTED_PAGES = 8
EXPECTED_SIZE = (1600, 900)
CHROME_STRIP = (0, 15, 1600, 35)
BLANK_STDDEV = 12
CHROME_RATIO = 0.35


def pdf_pages(data: bytes) -> int:
    counts = [int(value) for value in re.findall(rb"/Count\s+(\d+)", data)]
    direct = len(re.findall(rb"/Type\s*/Page[^s]", data))
    return max([direct, *counts], default=0)


def top_grey_ratio(image: Image.Image) -> float:
    """Window chrome shows a light-grey band (#F3F3F3) at the top; clean pages are white.

    Calibration: screenshots with the Power BI banner ≈ 0.71, rendered slides ≈ 0.05.
    """
    strip = image.crop(CHROME_STRIP).convert("L")
    histogram = strip.histogram()
    total = sum(histogram)
    return sum(histogram[236:251]) / total if total else 0.0


def main() -> None:
    problems: list[str] = []
    warnings: list[str] = []

    if not PDF.exists():
        problems.append("缺少 dashboards/看板.pdf")
    else:
        pages = pdf_pages(PDF.read_bytes())
        print(f"PDF: {pages} 页，{PDF.stat().st_size / 1e6:.2f} MB")
        if pages != EXPECTED_PAGES:
            problems.append(f"PDF 页数为 {pages}，期望 {EXPECTED_PAGES}")

    files = sorted(IMAGES.glob("page*.png"))
    print(f"截图: {len(files)} 张")
    if len(files) != EXPECTED_PAGES:
        problems.append(f"截图数量为 {len(files)}，期望 {EXPECTED_PAGES}")

    for path in files:
        with Image.open(path) as image:
            size = image.size
            stats = ImageStat.Stat(image.convert("L"))
            grey = top_grey_ratio(image)
        print(f"  {path.name}: {size[0]}x{size[1]}, 灰度标准差 {stats.stddev[0]:.1f}, 顶部灰带 {grey:.2f}")
        if size != EXPECTED_SIZE:
            problems.append(f"{path.name} 尺寸 {size}，期望 {EXPECTED_SIZE}")
        if stats.stddev[0] < BLANK_STDDEV:
            problems.append(f"{path.name} 接近空白页（标准差 {stats.stddev[0]:.1f}）")
        if grey > CHROME_RATIO:
            problems.append(f"{path.name} 顶部有应用界面灰带（占比 {grey:.2f}），不是纯报表内容")

    if warnings:
        print("\n提醒:")
        for warning in warnings:
            print("  -", warning)
    if problems:
        print("\n不可发布:")
        for problem in problems:
            print("  -", problem)
        raise SystemExit(1)
    print("\n资源检查通过")


if __name__ == "__main__":
    sys.exit(main())
