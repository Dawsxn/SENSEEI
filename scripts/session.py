#!/usr/bin/env python3
"""Play one SEE-I tutoring session in the terminal.

A harness, not the app. It exists so the Tutor Agent can be judged before any
database, server or UI exists. The loop rules live here for now; they move into
the Orchestrator when the backend is built.

    python scripts/session.py                     pick a text, real models
    python scripts/session.py --reading strategy
    python scripts/session.py --offline           no API calls, no cost
    python scripts/session.py --offline --pass-on 9   never passes, hits fallback
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "assessment-agent-eval" / "data"

# Windows consoles default to a legacy codepage; this output is not ASCII.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import agents  # noqa: E402
from agents.assessment import AssessmentAgent  # noqa: E402
from agents.providers import get_provider  # noqa: E402
from agents.rubric import criteria_for, load_rubric, render_rubric, steps  # noqa: E402
from agents.tutor import FINAL_FAIL, FIRST_ATTEMPT, PASSED, RETRY, TutorAgent  # noqa: E402

AGENTS = Path(agents.__file__).resolve().parent

# Provisional, per docs/context/student-tutoring-loop.md. One place, one edit.
MAX_ATTEMPTS = 3

# Static, not written by the Tutor: it is the same sentence every time, and
# generating it invites the model to soften it or add a hint nobody can use.
FALLBACK = ("You have used all your attempts for this step. Your instructor has "
            "been notified and can go through it with you.")

DIM, BOLD, GREEN, RED, RESET = "\033[2m", "\033[1m", "\033[32m", "\033[31m", "\033[0m"


# ----------------------------------------------------------------- offline stubs

class _StubProvider:
    """Deterministic stand-in so the loop can be exercised with no API calls."""

    def __init__(self, kind: str, pass_on: int):
        self.kind, self.pass_on = kind, pass_on
        self.seen: dict[str, int] = {}
        self.last_usage = None
        self.last_finish_reason = "STOP"

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        step = _between(user_prompt, "# CURRENT SEE-I STEP\n")
        if self.kind == "tutor":
            situation = _between(user_prompt, "# SITUATION\n")
            return f"[stub tutor] {step}: {situation[:70]}"
        n = self.seen[step] = self.seen.get(step, 0) + 1
        passing = n >= self.pass_on
        crits = criteria_for(step)
        failed = [] if passing else crits[:1]
        return json.dumps({
            "verdict": "PASS" if passing else "FAIL",
            "fail_criteria": failed,
            "criteria": {
                c: {"pass": c not in failed,
                    "reason": "[stub] ok" if c not in failed else "[stub] not met"}
                for c in crits
            },
        })


def _between(text: str, header: str) -> str:
    if header not in text:
        return ""
    return text.split(header, 1)[1].split("\n\n", 1)[0].strip()


# ----------------------------------------------------------------- setup

def load_readings() -> dict[str, dict]:
    """Unique readings from the eval dataset, with their core components."""
    out: dict[str, dict] = {}
    csv_path = sorted(DATA.glob("example_set_v*.csv"))[-1]
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            fname = row["reading_filename"].strip()
            if fname and fname not in out:
                out[fname] = {
                    "filename": fname,
                    "name": Path(fname).stem,
                    "core_components": (row.get("core_components") or "").strip(),
                }
    return out


def choose_reading(readings: dict[str, dict], wanted: str | None) -> dict:
    if wanted:
        for r in readings.values():
            if wanted.lower() in r["name"].lower():
                return r
        sys.exit(f"No reading matching {wanted!r}. Have: "
                 f"{', '.join(r['name'] for r in readings.values())}")
    listed = list(readings.values())
    print("\nAvailable texts:")
    for i, r in enumerate(listed, 1):
        print(f"  {i}. {r['name']}")
    while True:
        raw = input("\nPick one: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(listed):
            return listed[int(raw) - 1]


def build_agents(args):
    if args.offline:
        return (AssessmentAgent(_StubProvider("assess", args.pass_on), ""),
                TutorAgent(_StubProvider("tutor", args.pass_on), ""))

    from dotenv import load_dotenv
    load_dotenv(BASE / ".env")

    shared = {"provider": args.provider, "model": args.model,
              "temperature": 0, "max_output_tokens": 4096,
              "api_key_env": args.api_key_env, "thinking_level": args.thinking_level}

    assess_prompt = (AGENTS / "prompts" / f"system_prompt_{args.assessment_prompt}.md").read_text(encoding="utf-8")
    tutor_prompt = (AGENTS / "prompts" / f"tutor_prompt_{args.tutor_prompt}.md").read_text(encoding="utf-8")
    rubric_block = render_rubric()
    assess_prompt = assess_prompt.replace("{{RUBRIC}}", rubric_block)
    tutor_prompt = tutor_prompt.replace("{{RUBRIC}}", rubric_block)

    # The Assessment Agent returns JSON; the Tutor returns prose.
    return (AssessmentAgent(get_provider({**shared, "json_mode": True}), assess_prompt),
            TutorAgent(get_provider({**shared, "json_mode": False}), tutor_prompt))


# ----------------------------------------------------------------- the loop

def say(text: str):
    print(f"\n{BOLD}SENSEE-I{RESET}  {text}\n")


def run(args) -> dict:
    load_rubric(AGENTS / "rubrics" / f"rubric_{args.rubric}.yaml")
    readings = load_readings()
    reading = choose_reading(readings, args.reading)
    text = (DATA / "readings" / reading["filename"]).read_text(encoding="utf-8")
    assessor, tutor = build_agents(args)

    print(f"\n{'=' * 72}\n{BOLD}{reading['name']}{RESET}")
    for c in reading["core_components"].split("||"):
        if c.strip():
            print(f"  · {c.strip()}")
    print(f"{'=' * 72}")
    print(f"{DIM}Read it, then answer each step. Ctrl-C to quit.{RESET}")
    print(f"{DIM}{(DATA / 'readings' / reading['filename'])}{RESET}")

    turns, outcome = [], "complete"

    for step in steps():
        attempt = 0
        situation, response, unmet = FIRST_ATTEMPT, None, None

        while True:
            left = MAX_ATTEMPTS - attempt - 1
            msg = tutor.speak(text, step, situation,
                              core_components=reading["core_components"],
                              user_response=response, unmet=unmet,
                              attempts_left=left if situation == RETRY else None)
            if not msg.ok:
                print(f"{RED}Tutor failed: {msg.error}{RESET}")
                return {"outcome": "error", "turns": turns}
            say(msg.text)
            turns.append({"step": step, "situation": situation, "attempt": attempt,
                          "tutor": msg.text, "student": response, "unmet": unmet})

            if situation in (PASSED, FINAL_FAIL):
                break

            print(f"{DIM}{step} · attempt {attempt + 1} of {MAX_ATTEMPTS}{RESET}")
            response = input("you>  ").strip()
            if not response:
                continue

            print(f"{DIM}       grading...{RESET}")
            result = assessor.assess(text, step, response,
                                     key_concept=reading["core_components"])
            if not result.parse_ok or result.verdict not in ("PASS", "FAIL"):
                # A provider failure must never consume an attempt.
                print(f"{RED}       grading failed: {result.error or 'no verdict'}{RESET}")
                print(f"{DIM}       your attempt was not counted, try again{RESET}")
                continue

            attempt += 1
            if result.verdict == "PASS":
                print(f"{GREEN}       PASS{RESET}")
                situation, unmet = PASSED, None
            else:
                unmet = [(c, result.criteria[c].reason) for c in result.fail_criteria]
                print(f"{RED}       FAIL  {', '.join(result.fail_criteria)}{RESET}")
                situation = RETRY if attempt < MAX_ATTEMPTS else FINAL_FAIL

        if situation == FINAL_FAIL:
            print(f"{RED}{FALLBACK}{RESET}\n")
            outcome = "failed"
            break

    print(f"\n{'=' * 72}")
    print(f"Session {outcome}.")
    return {"outcome": outcome, "turns": turns}


def main():
    ap = argparse.ArgumentParser(description="Play one SEE-I session in the terminal")
    ap.add_argument("--reading", help="match part of a reading name")
    ap.add_argument("--provider", default="gemini")
    ap.add_argument("--model", default="gemini-3.1-pro-preview")
    ap.add_argument("--api-key-env", default="GEMINI_API_KEY")
    ap.add_argument("--thinking-level", default="low")
    ap.add_argument("--rubric", default="v3")
    ap.add_argument("--tutor-prompt", default="v1")
    ap.add_argument("--assessment-prompt", default="v3")
    ap.add_argument("--offline", action="store_true", help="stub both agents, no API calls")
    ap.add_argument("--pass-on", type=int, default=2,
                    help="offline only: attempt number that passes (set high to force fallback)")
    args = ap.parse_args()

    try:
        session = run(args)
    except KeyboardInterrupt:
        print("\nstopped")
        return

    out_dir = BASE / "scripts" / "runs"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = out_dir / f"{stamp}_{args.tutor_prompt}.json"
    path.write_text(json.dumps({
        "meta": {"tutor_prompt": args.tutor_prompt, "rubric": args.rubric,
                 "assessment_prompt": args.assessment_prompt,
                 "provider": "offline" if args.offline else args.provider,
                 "model": "offline" if args.offline else args.model,
                 "max_attempts": MAX_ATTEMPTS, "timestamp": stamp},
        **session,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Transcript: {path}")


if __name__ == "__main__":
    main()
