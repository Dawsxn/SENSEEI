#!/usr/bin/env python3
"""Render a session transcript as scripts/sample-session.md.

Transcripts under scripts/runs/ are gitignored. This turns one of them into a
committed, readable sample so the Tutor Agent's output can be read without an API
key. Run it after a session you think is worth keeping.

    python scripts/render_sample.py                 the newest transcript
    python scripts/render_sample.py runs/2026....json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
OUT = BASE / "sample-session.md"

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def newest() -> Path:
    runs = sorted((BASE / "runs").glob("*.json"), key=lambda p: p.stat().st_mtime)
    if not runs:
        sys.exit("No transcripts in scripts/runs/. Play a session first.")
    return runs[-1]


def render(data: dict) -> str:
    m, u = data["meta"], data.get("usage") or {}
    total = u.get("total", {})

    rows = [
        ("Text", m.get("reading", "unknown")),
        ("Steps", m.get("step", "all")),
        ("Tutor prompt", f"`{m['tutor_prompt']}`"),
        ("Assessment prompt", f"`{m['assessment_prompt']}`"),
        ("Rubric", f"`{m['rubric']}`"),
        ("Model", m["model"]),
        ("Attempts per step", m["max_attempts"]),
        ("Outcome", data["outcome"]),
    ]
    if total.get("calls"):
        rows.append(("Calls", f"{total['calls']} "
                              f"({u['tutor']['calls']} tutor, "
                              f"{u['assessment']['calls']} assessment)"))
    if total.get("input_tokens"):
        rows.append(("Tokens", f"{total['input_tokens']:,} in, "
                               f"{total['thinking_tokens']:,} thinking, "
                               f"{total['output_tokens']:,} out"))
        rows.append(("Estimated cost", f"${total['est_cost_usd']:.4f}"))

    out = [
        "# Sample session",
        "",
        "One real run of `scripts/session.py`, kept so the Tutor Agent's output can be",
        "read without spending anything. Illustrative, not a fixture: nothing tests",
        "against it.",
        "",
        "Regenerate with `python scripts/render_sample.py` after a session worth keeping.",
        "",
        "| | |",
        "| --- | --- |",
    ]
    out += [f"| {k} | {v} |" for k, v in rows]
    out += ["", "Some answers below are written to fail a specific criterion on purpose.", "", "---"]

    step = None
    for t in data["turns"]:
        if t["step"] != step:
            step = t["step"]
            out += ["", f"## {step}", ""]
        if t.get("student"):
            out += ["**Student**", "", f"> {t['student']}", ""]
        if t.get("unmet"):
            names = ", ".join(f"`{c}`" for c, _ in t["unmet"])
            out += [f"**Assessment Agent:** FAIL on {names}", ""]
        elif t["situation"] == "passed":
            out += ["**Assessment Agent:** PASS", ""]
        label = "Fallback" if t["situation"] == "fallback" else "Tutor"
        out += [f"**{label}**", "", f"> {t['tutor']}", ""]

    return "\n".join(out).rstrip() + "\n"


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else newest()
    if not src.is_absolute():
        src = (BASE / src) if (BASE / src).exists() else src
    data = json.loads(src.read_text(encoding="utf-8"))

    if data["meta"]["provider"] == "offline":
        sys.exit(f"{src.name} is an offline run. The sample should show real output.")

    OUT.write_text(render(data), encoding="utf-8")
    print(f"{src.name} -> {OUT.relative_to(BASE.parent)}")


if __name__ == "__main__":
    main()
