"""Check dashboard exports before publishing: page count, sizes, blank pages, app chrome.

Run after re-exporting from Power BI:
    python scripts/check_dashboard_assets.py

Exit code 1 means the assets are not publishable yet.
"""

from __future__ import annotations

import hashlib
import re
import sys
from collections import Counter
from pathlib import Path

from PIL import Image, ImageStat

ROOT = Path(__file__).resolve().parents[1]
IMAGES = ROOT / "dashboards" / "images"
PDF = ROOT / "dashboards" / "看板.pdf"
EXPECTED_PAGES = 8
EXPECTED_SIZE = (1600, 900)
CHROME_STRIP = (0, 15, 1600, 45)
BLANK_STDDEV = 12


def pdf_pages(data: bytes) -> int:
    counts = [int(value) for value in re.findall(rb"/Count\s+(\d+)", data)]
    direct = len(re.findall(rb"/Type\s*/Page[^s]", data))
    return max([direct, *counts], default=0)


def chrome_signature(image: Image.Image) -> str:
    strip = image.crop(CHROME_STRIP).convert("L")
    return hashlib.sha256(strip.tobytes()).hexdigest()[:12]


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

    signatures: dict[str, str] = {}
    for path in files:
        with Image.open(path) as image:
            size = image.size
            stats = ImageStat.Stat(image.convert("L"))
            blank = stats.stddev[0] < BLANK_STDDEV
            signatures[path.name] = chrome_signature(image)
        print(f"  {path.name}: {size[0]}x{size[1]}, 灰度标准差 {stats.stddev[0]:.1f}")
        if size != EXPECTED_SIZE:
            problems.append(f"{path.name} 尺寸 {size}，期望 {EXPECTED_SIZE}")
        if blank:
            problems.append(f"{path.name} 接近空白页（标准差 {stats.stddev[0]:.1f}）")

    if signatures:
        repeated, count = Counter(signatures.values()).most_common(1)[0]
        if count >= max(2, len(signatures) * 0.8):
            names = [name for name, sig in signatures.items() if sig == repeated]
            problems.append(
                "截图顶部包含相同的应用界面条（Power BI 标题栏/自动恢复横幅），"
                f"共 {len(names)} 张：{', '.join(names[:3])}…；请在阅读视图重新导出"
            )

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
