"""Build the real-data edition. Raw files are obtained by scripts/download_data.py."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
# Offline fallback: a wheel unpacked into .localdeps (see docs/metrics.md).
for directory in (".localdeps", "src"):
    candidate = ROOT / directory
    if candidate.exists():
        sys.path.insert(0, str(candidate))

from pipeline import main

if __name__ == "__main__":
    main()
