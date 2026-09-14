#!/usr/bin/env python3
"""Render a .dc.html artboard to PNG by standing in for the canvas runtime.

The artboards reference a ./support.js the canvas build supplies and this repo
does not carry, so opening one in a browser shows a grey skeleton. This resolves
the handful of template constructs the artboard actually uses -- {{value}},
<sc-if>, <sc-for> -- against the values its own DCLogic block returns, then hands
the result to headless Chrome.

Not a general template engine. It understands exactly what these artboards use,
and raises rather than guessing when it meets something else.

    python scripts/render_artboard.py design/ReadingStep.dc.html \
        design/png/03c-reading-step.png 1440 900 "state=Reading"

Rendered at 2x, so the PNGs in `design/png/` stay legible when zoomed. Needs
Chrome and node on PATH.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def extract_values(source: str, overrides: dict[str, str]) -> dict:
    """Run the artboard's renderVals() in node, so the PNG uses the real logic."""
    script = re.search(r"<script data-dc-script[^>]*>(.*?)</script>", source, re.S)
    if not script:
        raise SystemExit("no <script data-dc-script> block")

    harness = (
        "class DCLogic { constructor(p) { this.props = p; } }\n"
        + script.group(1)
        + f"\nconsole.log(JSON.stringify(new Component({json.dumps(overrides)}).renderVals()));"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(harness)
        path = f.name
    out = subprocess.run(["node", path], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def resolve(html: str, vals: dict) -> str:
    # <sc-for list="{{rows}}" as="r">...</sc-for> -- repeat the body per row
    def expand_for(m: re.Match) -> str:
        name, alias, body = m.group(1), m.group(2), m.group(3)
        out = []
        for row in vals.get(name, []):
            chunk = body
            for key, value in row.items():
                chunk = chunk.replace("{{%s.%s}}" % (alias, key), str(value))
            out.append(chunk)
        return "".join(out)

    html = re.sub(
        r'<sc-for list="\{\{(\w+)\}\}" as="(\w+)"[^>]*>(.*?)</sc-for>',
        expand_for, html, flags=re.S,
    )

    # <sc-if value="{{flag}}">...</sc-if> -- keep the body only when truthy
    html = re.sub(
        r'<sc-if value="\{\{(\w+)\}\}"[^>]*>(.*?)</sc-if>',
        lambda m: m.group(2) if vals.get(m.group(1)) else "",
        html, flags=re.S,
    )

    # plain {{value}} substitutions
    html = re.sub(r"\{\{(\w+)\}\}", lambda m: str(vals.get(m.group(1), "")), html)

    # the canvas runtime supplies these; strip what is left
    html = html.replace('<script src="./support.js"></script>', "")
    html = re.sub(r"<script data-dc-script.*?</script>", "", html, flags=re.S)
    html = html.replace("<x-dc>", "").replace("</x-dc>", "")
    html = html.replace("<helmet>", "").replace("</helmet>", "")
    return html


def main() -> None:
    src, out = Path(sys.argv[1]), Path(sys.argv[2]).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    width = int(sys.argv[3]) if len(sys.argv) > 3 else 1440
    height = int(sys.argv[4]) if len(sys.argv) > 4 else 900
    overrides = dict(a.split("=", 1) for a in sys.argv[5:])

    source = src.read_text(encoding="utf-8")
    html = resolve(source, extract_values(source, overrides))

    staged = src.parent / f".render-{src.stem}.html"
    staged.write_text(html, encoding="utf-8")
    try:
        with tempfile.TemporaryDirectory() as profile:
            subprocess.run(
                [CHROME, "--headless", "--disable-gpu", f"--user-data-dir={profile}",
                 "--hide-scrollbars", "--default-background-color=ffffff",
                 "--force-device-scale-factor=2",
                 f"--window-size={width},{height}", f"--screenshot={out}",
                 staged.resolve().as_uri()],
                check=True, timeout=120,
            )
    finally:
        staged.unlink(missing_ok=True)
    print(f"wrote {out.name} ({out.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
