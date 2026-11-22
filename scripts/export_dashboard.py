"""Export dashboards/静态看板.pptx to 8 PNG (1600x900) and a PDF, without manual clicks.

PowerPoint is driven through COM (pywin32, Unicode-safe). The PDF is assembled from the
exported PNGs with Pillow, so the pipeline does not depend on PowerPoint's PDF writer.

Usage:
    python scripts/export_dashboard.py
"""

from __future__ import annotations

import os
import shutil
import sys
import uuid
import gc
from pathlib import Path

from PIL import Image
import PIL.JpegImagePlugin  # registers the JPEG encoder used by Pillow's PDF writer (noqa: F401)

ROOT = Path(__file__).resolve().parents[1]
DEPS = ROOT / ".localdeps"
sys.path[:0] = [str(DEPS), str(DEPS / "win32"), str(DEPS / "win32" / "lib")]

SOURCE = ROOT / "dashboards" / "静态看板.pptx"
IMAGES = ROOT / "dashboards" / "images"
PDF = ROOT / "dashboards" / "看板.pdf"
TEMP = ROOT / ".work" / "pptx-export"
SIZE = (1600, 900)


def _powerpoint():
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    return win32com.client.DispatchEx("PowerPoint.Application")


def export_png() -> list[Path]:
    app = _powerpoint()
    try:
        presentation = app.Presentations.Open(str(SOURCE), ReadOnly=True, WithWindow=False)
        TEMP.mkdir(parents=True, exist_ok=True)
        for old in TEMP.glob("*.PNG"):
            old.unlink()
        presentation.Export(str(TEMP), "PNG", SIZE[0], SIZE[1])
        presentation.Close()
    finally:
        app.Quit()
    slides = sorted(TEMP.glob("*.PNG"), key=lambda path: int("".join(filter(str.isdigit, path.stem)) or 0))
    if len(slides) != 8:
        raise SystemExit(f"expected 8 slides, got {len(slides)}")
    return slides


def export_pdf() -> None:
    """A second, fresh PowerPoint session: Export + SaveAs in one session crashes on this box."""
    app = _powerpoint()
    try:
        presentation = app.Presentations.Open(str(SOURCE), ReadOnly=True, WithWindow=False)
        presentation.SaveAs(str(PDF), 32)  # 32 = ppSaveAsPDF
        presentation.Close()
    finally:
        app.Quit()


def main() -> None:
    if sys.platform != "win32":
        raise SystemExit("Rendering needs Windows + installed Microsoft PowerPoint. Use committed HTML/PNG/PDF on other platforms.")
    if hasattr(os, "add_dll_directory") and (DEPS / "pywin32_system32").exists():
        os.add_dll_directory(str(DEPS / "pywin32_system32"))
    slides = export_png()
    stage = TEMP / ("bundle-" + uuid.uuid4().hex)
    stage.mkdir()
    pairs = []
    for index, slide in enumerate(slides, start=1):
        target = stage / f"page{index:02d}.png"
        shutil.copyfile(slide, target)
        with Image.open(target) as image:
            if image.size != SIZE:
                raise SystemExit(f"{target.name}: unexpected size {image.size}")
        pairs.append((target, IMAGES / target.name))
    pages = [Image.open(p).convert("RGB") for p,_ in pairs]
    staged_pdf = stage / PDF.name
    with staged_pdf.open('wb') as stream:
        pages[0].save(stream, format='PDF', save_all=True, append_images=pages[1:], resolution=150.0)
    for page in pages:
        page.close()
    gc.collect()
    sys.path.insert(0, str(ROOT / "src"))
    from publish import publish_bundle
    publish_bundle(pairs + [(staged_pdf, PDF)], ROOT / ".work")
    from dashboard_contract import write_manifest
    write_manifest()
    print(f"PDF: {PDF.relative_to(ROOT)} ({PDF.stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
