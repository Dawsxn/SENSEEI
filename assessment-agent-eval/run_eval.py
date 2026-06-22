#!/usr/bin/env python3
"""Run the labeled example set through the Student Assessment Agent and emit an
HTML report comparing the agent's verdict/criteria against the expected labels.

Versioned inputs (prompt / rubric / example set) are pinned in config.yaml and
stamped on every output. Override any of them per-run with an explicit path.

Examples
--------
  python run_eval.py                      # full run with config.yaml version pins
  python run_eval.py --provider mock      # offline smoke test (no API key)
  python run_eval.py --limit 4            # quick run on the first 4 rows
  python run_eval.py --prompt prompts/system_prompt_v2.md   # override prompt
  python run_eval.py --rubric rubric/rubric_v1.yaml --csv data/example_set_v1.csv
  python run_eval.py --from-run runs/20260618_101500_v2     # rebuild report, no API calls
"""

from __future__ import annotations

import argparse
import csv
import glob
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

# make `src` importable regardless of where the script is launched from
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

# Windows consoles default to a legacy codepage (cp1252); paths/output here can
# contain non-ASCII (e.g. Japanese folder names), so force UTF-8 for stdout/stderr.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from src.agent import AgentResult, AssessmentAgent  # noqa: E402
from src.compare import compare, parse_expected_criteria, summarize  # noqa: E402
from src.providers import get_provider  # noqa: E402
from src.report import render_report  # noqa: E402
from src.rubric import load_rubric, render_rubric, steps  # noqa: E402


# ---------------------------------------------------------------- config / prompt

def load_config(path: Path) -> dict:
    import yaml
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def select_prompt(prompts_dir: Path, explicit: str | None) -> tuple[Path, str, str, str]:
    """Return (path, version_label, short_hash, text). Defaults to the highest vN."""
    if explicit:
        path = Path(explicit)
        if not path.is_absolute():
            path = BASE / path
    else:
        files = glob.glob(str(prompts_dir / "system_prompt_v*.md"))
        if not files:
            raise FileNotFoundError(f"No system_prompt_v*.md found in {prompts_dir}")
        path = Path(max(files, key=_version_number))
    text = path.read_text(encoding="utf-8")
    version = _version_label(path)
    short_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:10]
    return path, version, short_hash, text


def _version_number(p: str) -> int:
    m = re.search(r"v(\d+)", Path(p).name)
    return int(m.group(1)) if m else 0


def _version_label(path, fallback: str = "custom") -> str:
    """Pull a 'vN' label out of a filename (e.g. rubric_v2.yaml -> 'v2')."""
    m = re.search(r"v(\d+)", Path(path).name)
    return f"v{m.group(1)}" if m else fallback


def _resolve_input(cli_value, base_dir: Path, pattern: str, version: str) -> Path:
    """CLI explicit path wins; otherwise build base_dir / pattern.format(version)."""
    if cli_value:
        p = Path(cli_value)
        return p if p.is_absolute() else BASE / p
    return base_dir / pattern.format(version)


# ---------------------------------------------------------------- record building

def build_records(examples: list[dict]):
    """From stored example dicts (each with an embedded agent result), build the
    records the summary + template need. Used for both live runs and --from-run."""
    summary_records, template_records = [], []
    for ex in examples:
        result = AgentResult.from_dict(ex["result"])
        comp = compare(ex["expected_verdict"], ex["expected_criteria"], result)
        summary_records.append({
            "id": ex["id"], "step": ex["step"],
            "expected_verdict": ex["expected_verdict"], "comparison": comp,
        })
        template_records.append({
            "id": ex["id"], "step": ex["step"],
            "learning_objective": ex.get("learning_objective", ""),
            "user_response": ex["user_response"],
            "expected_verdict": comp.expected_verdict,
            "expected_criteria": comp.expected_criteria,
            "actual_verdict": comp.actual_verdict,
            "actual_criteria": comp.actual_criteria,
            "matched": comp.matched, "missed": comp.missed, "extra": comp.extra,
            "status": comp.status,
            "criteria": {k: {"passed": v.passed, "reason": v.reason}
                         for k, v in result.criteria.items()},
            "warnings": result.warnings, "error": result.error,
            "finish_reason": result.finish_reason,
            "notes": ex.get("notes", ""),
        })
    return summary_records, template_records


# ---------------------------------------------------------------- outputs

def write_report(meta: dict, summary: dict, template_records: list[dict],
                 reports_dir: Path) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    out = reports_dir / f"{meta['timestamp']}_{meta['prompt_version']}.html"
    out.write_text(render_report(meta, summary, template_records), encoding="utf-8")
    return out


def compute_cost(examples: list[dict], price_in: float, price_out: float) -> dict:
    """Sum token usage across the run and estimate USD cost.

    Thinking tokens bill at the output rate, so billed output = output + thinking.
    Returns None token fields if no example reported usage (e.g. an old run).
    """
    ti = to = tt = 0
    have_usage = False
    for ex in examples:
        u = (ex.get("result") or {}).get("usage") or {}
        if u:
            have_usage = True
        ti += u.get("input_tokens", 0) or 0
        to += u.get("output_tokens", 0) or 0
        tt += u.get("thinking_tokens", 0) or 0
    billed_out = to + tt
    est = ti / 1e6 * price_in + billed_out / 1e6 * price_out
    return {
        "input_tokens": ti if have_usage else None,
        "output_tokens": to if have_usage else None,
        "thinking_tokens": tt if have_usage else None,
        "est_cost_usd": est if have_usage else None,
        "price_input_per_1m": price_in,
        "price_output_per_1m": price_out,
    }


def append_results_log(log_path: Path, meta: dict, summary: dict, report_file: Path):
    per_step = {s["step"]: s["accuracy"] for s in summary["per_step"]}
    cost = meta.get("cost") or {}
    header = ["timestamp", "prompt_version", "rubric_version", "example_set_version",
              "prompt_hash", "provider", "model", "thinking_level",
              "total", "verdict_accuracy", *steps(), "criteria_exact_rate",
              "input_tokens", "thinking_tokens", "output_tokens", "est_cost_usd",
              "report_file"]

    def cell(key, ndigits=None):
        v = cost.get(key)
        if v is None:
            return ""
        return round(v, ndigits) if ndigits is not None else v

    row = [meta["timestamp"], meta["prompt_version"], meta.get("rubric_version", ""),
           meta.get("example_set_version", ""), meta["prompt_hash"],
           meta["provider"], meta["model"], meta.get("thinking_level", ""),
           summary["total"],
           round(summary["verdict_accuracy"], 4),
           *[round(per_step.get(s, 0.0), 4) for s in steps()],
           round(summary["criteria_exact_rate"], 4),
           cell("input_tokens"), cell("thinking_tokens"), cell("output_tokens"),
           cell("est_cost_usd", 4),
           report_file.name]
    new = not log_path.exists()
    for attempt in range(3):  # OneDrive/Excel can briefly lock the file
        try:
            with open(log_path, "a", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                if new:
                    w.writerow(header)
                w.writerow(row)
            return
        except OSError as e:
            if attempt < 2:
                time.sleep(0.7)
                continue
            print(f"  ! Could not append to {log_path.name} ({e}). "
                  f"Is it open in Excel / syncing in OneDrive? The report was still "
                  f"saved; close the file and this row won't be logged for this run.")


def print_summary(summary: dict):
    print(f"\nVerdict accuracy: {summary['verdict_accuracy']*100:.1f}% "
          f"({summary['verdict_correct']}/{summary['total']})")
    print(f"Criteria exact-match (FAILs): {summary['criteria_exact_rate']*100:.1f}% "
          f"({summary['criteria_exact']}/{summary['fail_n']})")
    for s in summary["per_step"]:
        print(f"  {s['step']:<11} {s['accuracy']*100:5.1f}%  ({s['correct']}/{s['n']})")
    sc = summary["status_counts"]
    print(f"Status: agree={sc['agree']} criteria_diff={sc['criteria_diff']} "
          f"verdict_diff={sc['verdict_diff']} error={sc['error']}")


# ---------------------------------------------------------------- main

def run_live(args) -> tuple[dict, list[dict]]:
    from dotenv import load_dotenv
    load_dotenv(BASE / ".env")

    config = load_config(BASE / args.config)
    if args.provider:
        config["provider"] = args.provider
    if args.model:
        config["model"] = args.model

    # Resolve the versioned inputs. An explicit CLI path overrides the config pin.
    rubric_path = _resolve_input(args.rubric, BASE / "rubric", "rubric_{}.yaml",
                                 config.get("rubric_version", "v2"))
    csv_path = _resolve_input(args.csv, BASE / "data", "example_set_{}.csv",
                              config.get("example_set_version", "v2"))
    prompt_pin = None if args.prompt else str(
        BASE / "prompts" / f"system_prompt_{config.get('prompt_version', 'v2')}.md")
    prompts_dir = BASE / "prompts"
    readings_dir = csv_path.parent / "readings"

    rubric_version = _version_label(rubric_path)
    example_set_version = _version_label(csv_path)
    load_rubric(rubric_path)  # active for parsing, validation, and stats

    prompt_path, version, _filehash, prompt_text = select_prompt(prompts_dir, args.prompt or prompt_pin)
    # Compose the prompt: inject the rubric into the {{RUBRIC}} placeholder (if any),
    # and hash what the model ACTUALLY sees (prompt + rubric together).
    system_prompt = prompt_text
    if "{{RUBRIC}}" in system_prompt:
        system_prompt = system_prompt.replace("{{RUBRIC}}", render_rubric())
    prompt_hash = hashlib.sha256(system_prompt.encode("utf-8")).hexdigest()[:10]

    provider = get_provider(config)
    agent = AssessmentAgent(provider, system_prompt)
    retries = int(config.get("retries", 1))

    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if args.limit:
        rows = rows[: args.limit]

    # Free tiers cap requests-per-minute; space calls out to stay under the limit.
    rpm = float(config.get("requests_per_minute", 0) or 0)
    min_interval = 60.0 / rpm if rpm > 0 else 0.0
    next_allowed = 0.0

    reading_cache: dict[str, str] = {}
    examples = []
    throttle_note = f" · throttled to {rpm:g}/min" if rpm > 0 else ""
    print(f"Prompt {version} ({prompt_hash}) · rubric {rubric_version} · "
          f"examples {example_set_version} · provider={config['provider']} "
          f"model={config.get('model')} · {len(rows)} examples{throttle_note}")
    for i, row in enumerate(rows, 1):
        if min_interval:
            wait = next_allowed - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            next_allowed = time.monotonic() + min_interval
        fname = row["reading_filename"].strip()
        if fname not in reading_cache:
            reading_cache[fname] = (readings_dir / fname).read_text(encoding="utf-8")
        step = row["seei_step"].strip()
        result = agent.assess(
            reading=reading_cache[fname],
            learning_objective=row["learning_objective"].strip(),
            seei_step=step,
            user_response=row["user_response"].strip(),
            retries=retries,
        )
        flag = "ok " if result.parse_ok and result.verdict else "ERR"
        print(f"  [{i:>2}/{len(rows)}] {row['id']:<10} {step:<10} -> "
              f"{result.verdict or '—':<4} {flag}")
        examples.append({
            "id": row["id"], "step": step,
            "learning_objective": row["learning_objective"].strip(),
            "user_response": row["user_response"].strip(),
            "expected_verdict": row["expected_verdict"].strip(),
            "expected_criteria": parse_expected_criteria(row.get("criterion_targeted", ""), step),
            "criterion_targeted": row.get("criterion_targeted", "").strip(),
            "notes": (row.get("rationale") or row.get("notes") or "").strip(),
            "result": result.to_dict(),
        })

    meta = {
        "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "prompt_version": version, "prompt_hash": prompt_hash,
        "prompt_file": prompt_path.name,
        "rubric_version": rubric_version, "rubric_file": rubric_path.name,
        "example_set_version": example_set_version,
        "provider": config["provider"], "model": config.get("model", ""),
        "thinking_level": config.get("thinking_level") or "",
        "csv": csv_path.name,
    }
    meta["cost"] = compute_cost(
        examples,
        float(config.get("price_input_per_1m", 2.0)),
        float(config.get("price_output_per_1m", 12.0)),
    )

    # persist raw run for reproducibility / offline re-reporting
    run_dir = BASE / "runs" / f"{meta['timestamp']}_{version}"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "results.json").write_text(
        json.dumps({"meta": meta, "examples": examples}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return meta, examples


def load_run(path: str) -> tuple[dict, list[dict]]:
    p = Path(path)
    if not p.is_absolute():
        p = BASE / p
    if p.is_dir():
        p = p / "results.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    return data["meta"], data["examples"]


def main():
    ap = argparse.ArgumentParser(description="SENSEEI Student Assessment Agent eval runner")
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--csv", default=None,
                    help="explicit example-set CSV path (overrides config example_set_version)")
    ap.add_argument("--prompt", default=None,
                    help="explicit system_prompt path (overrides config prompt_version)")
    ap.add_argument("--rubric", default=None,
                    help="explicit rubric YAML path (overrides config rubric_version)")
    ap.add_argument("--limit", type=int, default=0, help="only run the first N rows")
    ap.add_argument("--provider", default=None, help="override config provider (e.g. mock)")
    ap.add_argument("--model", default=None, help="override config model")
    ap.add_argument("--from-run", default=None, help="rebuild report from a saved runs/ dir (no API calls)")
    args = ap.parse_args()

    if args.from_run:
        meta, examples = load_run(args.from_run)
        # make the rubric that run used active (for validation + per-criterion stats)
        cfg = load_config(BASE / args.config)
        rubric_path = _resolve_input(
            args.rubric, BASE / "rubric", "rubric_{}.yaml",
            meta.get("rubric_version") or cfg.get("rubric_version", "v2"))
        load_rubric(rubric_path)
        # stamp a fresh report timestamp so we don't overwrite the original
        meta = {**meta, "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S")}
    else:
        meta, examples = run_live(args)  # loads the rubric internally

    if not meta.get("cost"):  # e.g. rebuilding from an old run that lacked usage
        cfg = load_config(BASE / args.config)
        meta["cost"] = compute_cost(
            examples,
            float(cfg.get("price_input_per_1m", 2.0)),
            float(cfg.get("price_output_per_1m", 12.0)),
        )

    summary_records, template_records = build_records(examples)
    summary = summarize(summary_records)
    report_path = write_report(meta, summary, template_records, BASE / "reports")
    if not args.from_run:
        append_results_log(BASE / "results_log.csv", meta, summary, report_path)

    print_summary(summary)
    cost = meta.get("cost") or {}
    if cost.get("est_cost_usd") is not None:
        print(f"Tokens: in={cost['input_tokens']:,} thinking={cost['thinking_tokens']:,} "
              f"out={cost['output_tokens']:,}  |  est cost ${cost['est_cost_usd']:.4f} USD")
    print(f"\nReport: {report_path}")


if __name__ == "__main__":
    main()
