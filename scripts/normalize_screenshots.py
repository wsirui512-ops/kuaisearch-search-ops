"""Normalize dashboard screenshots to exactly 1600x900 without distorting the chart area.

Dashboard screenshots rarely come out at the exact size. This script centre-crops the
image to 16:9 and resizes it, so `check_dashboard_assets.py` can pass.

Usage:
    python scripts/normalize_screenshots.py                 # all page*.png in dashboards/images
    python scripts/normalize_screenshots.py --trim-top 60   # drop window chrome first
    python scripts/normalize_screenshots.py --dry-run       # report sizes only
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
IMAGES = ROOT / "dashboards" / "images"
TARGET = (1600, 900)


def normalize(path: Path, trim_top: int, trim_bottom: int, dry_run: bool) -> str:
    with Image.open(path) as image:
        original = image.size
        width, height = image.size
        bottom = height - trim_bottom
        top = trim_top
        if bottom - top <= 0:
            raise ValueError(f"{path.name}: trim removes the whole image")
        # keep the aspect ratio the target needs: crop width or height symmetrically
        target_ratio = TARGET[0] / TARGET[1]
        crop_height = bottom - top
        crop_width = width
        if crop_width / crop_height > target_ratio:
            crop_width = int(crop_height * target_ratio)
        else:
            crop_height = int(crop_width / target_ratio)
        left = (width - crop_width) // 2
        upper = top + ((bottom - top) - crop_height) // 2
        box = (left, upper, left + crop_width, upper + crop_height)
        if dry_run:
            return f"{path.name}: {original} -> crop {crop_width}x{crop_height} -> {TARGET}"
        backup = IMAGES / "original"
        backup.mkdir(exist_ok=True)
        if not (backup / path.name).exists():
            shutil.copyfile(path, backup / path.name)
        normalized = image.crop(box).resize(TARGET, Image.LANCZOS)
        normalized.save(path, optimize=True)
        return f"{path.name}: {original} -> {TARGET}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trim-top", type=int, default=0, help="pixels of window chrome to drop from the top")
    parser.add_argument("--trim-bottom", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    files = sorted(IMAGES.glob("page*.png"))
    if not files:
        raise SystemExit(f"no page*.png under {IMAGES}")
    for path in files:
        print(normalize(path, args.trim_top, args.trim_bottom, args.dry_run))
    if not args.dry_run:
        print("\noriginals kept in dashboards/images/original/")


if __name__ == "__main__":
    main()
