#!/usr/bin/env python3
"""Render the tennis reading's PDF from its HTML source.

    python scripts/make_tennis_pdf.py

Three of the four seeded readings are real documents. This one is written, and
it exists for a specific reason: it is the only reading whose figures carry
information the prose does not spell out, which is what makes it a test of
whether the Assessment Agent still grades fairly when a student answers by
pointing at a figure.

The PDF is committed, so the seed needs neither this script nor a browser. Run
this only after editing `tennis_recovery.html`.

Chrome renders it rather than a Python PDF library because the figures are SVG
and the layout is CSS: the source stays editable as a web page, which is a much
shorter loop than redrawing diagrams in drawing primitives.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "scripts" / "fixtures" / "readings" / "tennis_recovery.html"
TARGET = ROOT / "scripts" / "fixtures" / "readings" / "tennis_recovery.pdf"

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
]


def find_chrome() -> str:
    for name in ("chrome", "google-chrome", "chromium"):
        found = shutil.which(name)
        if found:
            return found
    for path in CHROME_CANDIDATES:
        if Path(path).exists():
            return path
    raise SystemExit(
        "no Chrome found. Install it, or add its path to CHROME_CANDIDATES."
    )


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"missing source: {SOURCE}")

    # A throwaway profile: without one Chrome may attach to the running browser
    # and return before it has written anything.
    with tempfile.TemporaryDirectory() as profile:
        subprocess.run(
            [
                find_chrome(),
                "--headless",
                "--disable-gpu",
                f"--user-data-dir={profile}",
                "--no-pdf-header-footer",
                f"--print-to-pdf={TARGET}",
                SOURCE.as_uri(),
            ],
            check=True,
            timeout=120,
        )

    if not TARGET.exists():
        raise SystemExit("Chrome exited cleanly but wrote no PDF.")
    print(f"wrote {TARGET.relative_to(ROOT)} ({TARGET.stat().st_size:,} bytes)")


if __name__ == "__main__":
    sys.exit(main())
