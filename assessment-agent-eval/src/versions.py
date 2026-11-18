"""Versioned prompt and rubric files, for the local editor (``serve.py``).

A version is a file in the shared ``agents`` package: ``agents/prompts/system_prompt_vN.md`` or
``agents/rubrics/rubric_vN.yaml``. Saving never edits a file that exists: it writes the next number
(highest + 1) and logs who it was based on in ``versions.csv`` beside it. Prompts and rubrics are
numbered independently, as the config pins them separately.

Nothing here changes what runs. The eval uses the versions pinned in ``config.yaml`` and the
backend the ones in its settings; a new file is only used once someone pins it.

``base`` is always this ``assessment-agent-eval`` folder. The prompts and rubrics are read from
``base.parent / "agents"``, which is where the editable install (``pip install -e .``) puts the
package that ``run_eval.py`` and the backend import.
"""

from __future__ import annotations

import csv
import difflib
import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

KINDS = {
    "prompt": ("prompts", "system_prompt_v{n}.md", re.compile(r"^system_prompt_v(\d+)\.md$")),
    "rubric": ("rubrics", "rubric_v{n}.yaml", re.compile(r"^rubric_v(\d+)\.yaml$")),
}
STEPS = ("State", "Elaborate", "Exemplify", "Illustrate")
CONFIGS = ("config.yaml", "config.deepseek.yaml")
SLOT = "{{RUBRIC}}"
LOG_HEADER = ["version", "based_on", "saved_at", "note"]


class VersionError(ValueError):
    """The request cannot be turned into a new version; the message says why."""


@dataclass
class Check:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    diff: list[str] = field(default_factory=list)
    changed: bool = False


def agents_dir(base: Path) -> Path:
    return Path(base).resolve().parent / "agents"


def _dir(base: Path, kind: str) -> Path:
    if kind not in KINDS:
        raise VersionError(f"unknown kind {kind!r}; expected prompt or rubric")
    return agents_dir(base) / KINDS[kind][0]


def _number(n) -> int:
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise VersionError(f"version must be a positive whole number, got {n!r}")
    return n


def path_for(base: Path, kind: str, n: int) -> Path:
    return _dir(base, kind) / KINDS[kind][1].format(n=_number(n))


def list_versions(base: Path, kind: str) -> list[int]:
    """Only ``system_prompt_vN.md`` counts as a prompt, so the tutor and figure prompts that share
    ``agents/prompts/`` are never listed or numbered against."""
    folder, pattern = _dir(base, kind), KINDS[kind][2]
    if not folder.is_dir():
        return []
    return sorted(int(m.group(1)) for p in folder.iterdir() if (m := pattern.match(p.name)))


def next_version(base: Path, kind: str) -> int:
    found = list_versions(base, kind)
    return (found[-1] if found else 0) + 1


def normalize_text(text: str) -> str:
    """LF line endings and exactly one trailing newline, so a re-saved file is not a 'change'."""
    return text.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n") + "\n"


def read_version(base: Path, kind: str, n: int) -> str:
    path = path_for(base, kind, n)
    if not path.is_file():
        raise VersionError(f"{kind} v{n} does not exist")
    return path.read_text(encoding="utf-8")


def _load_yaml(text: str):
    import yaml
    try:
        return yaml.safe_load(text), None
    except yaml.YAMLError as e:
        return None, f"not valid YAML: {str(e).splitlines()[0] if str(e) else e}"


def _rubric_problems(text: str) -> tuple[list[str], dict]:
    data, problem = _load_yaml(text)
    if problem:
        return [problem], {}
    if not isinstance(data, dict):
        return ["the rubric must be a mapping of step -> criteria"], {}
    errors = []
    for step in STEPS:
        if step not in data:
            errors.append(f"missing step {step}")
    for step in data:
        if step not in STEPS:
            errors.append(f"unknown step {step!r}; the steps are {', '.join(STEPS)}")
    names: dict[str, list[str]] = {}
    for step in STEPS:
        crits = data.get(step)
        if step not in data:
            continue
        if not isinstance(crits, dict) or not crits:
            errors.append(f"{step} needs at least one criterion")
            continue
        names[step] = []
        for name, value in crits.items():
            condition = value.get("pass") if isinstance(value, dict) else value
            if not isinstance(condition, str) or not condition.strip():
                errors.append(f"{step} / {name} needs a non-empty pass condition")
            names[step].append(str(name))
    return errors, names


def _loose(name: str) -> str:
    """The loose matching the eval itself uses to read criterion names from the CSV."""
    from agents.rubric import normalize
    return normalize(name)


def example_set_criteria(base: Path) -> tuple[str, dict[str, set[str]]] | None:
    """The pinned example set's version and, per step, the criterion names it expects to fail.

    An example set lists only the criteria a response should FAIL (``criterion_targeted``, joined
    with ``+``), so this is the set of names a rubric must keep for those rows to be scored, not
    the full list of criteria. None when the config or the CSV cannot be read."""
    import yaml
    try:
        cfg = yaml.safe_load((Path(base) / "config.yaml").read_text(encoding="utf-8")) or {}
        version = str(cfg["example_set_version"])
        path = Path(base) / "data" / f"example_set_{version}.csv"
        with open(path, encoding="utf-8-sig", newline="") as f:
            out: dict[str, set[str]] = {}
            for row in csv.DictReader(f):
                for part in (row.get("criterion_targeted") or "").split("+"):
                    if part.strip():
                        out.setdefault((row.get("seei_step") or "").strip(), set()).add(part.strip())
        return version, out
    except (OSError, KeyError, yaml.YAMLError):
        return None


def check(base: Path, kind: str, text: str, based_on: int) -> Check:
    """Validate ``text`` and diff it against the version it was edited from."""
    result = Check()
    old = normalize_text(read_version(base, kind, based_on))
    new = normalize_text(text)
    result.changed = new != old
    result.diff = [line.rstrip("\n") for line in difflib.unified_diff(
        old.splitlines(), new.splitlines(), f"v{based_on}", "new", lineterm="", n=2)]
    if not text.strip():
        result.errors.append(f"the {kind} is empty")
        return result
    if kind == "prompt":
        if new.count(SLOT) != 1:
            result.errors.append(f"the prompt must contain {SLOT} exactly once "
                                 f"(found {new.count(SLOT)}); the rubric is inserted there")
        return result
    errors, names = _rubric_problems(new)
    result.errors.extend(errors)
    expected = example_set_criteria(base)
    if not errors and expected:
        version, by_step = expected
        for step in STEPS:
            mine = {_loose(n) for n in names.get(step, [])}
            for name in sorted(by_step.get(step, set())):
                if _loose(name) not in mine:
                    result.warnings.append(
                        f"{step}: example set {version} expects {name!r} to fail, but this rubric "
                        f"has no such criterion; those rows cannot match until the names agree")
    return result


def save_version(base: Path, kind: str, text: str, based_on: int, note: str = "") -> int:
    """Write ``text`` as the next version. Raises VersionError if it is invalid or unchanged."""
    result = check(base, kind, text, based_on)
    if result.errors:
        raise VersionError("; ".join(result.errors))
    if not result.changed:
        raise VersionError(f"no changes from v{based_on}; edit something first")
    folder = _dir(base, kind)
    folder.mkdir(parents=True, exist_ok=True)
    n = next_version(base, kind)
    while True:
        try:
            with open(path_for(base, kind, n), "x", encoding="utf-8", newline="\n") as f:
                f.write(normalize_text(text))
            break
        except FileExistsError:   # someone saved at the same moment: take the next number
            n += 1
    log = folder / "versions.csv"
    new_log = not log.exists() or not log.stat().st_size
    with open(log, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if new_log:
            w.writerow(LOG_HEADER)
        w.writerow([f"v{n}", f"v{based_on}", datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    " ".join(note.split())])
    return n


def pinned(base: Path) -> dict[str, dict[int, list[str]]]:
    """Which config files pin each version: {"prompt": {3: ["config.yaml"]}, "rubric": {...}}."""
    import yaml
    out: dict[str, dict[int, list[str]]] = {"prompt": {}, "rubric": {}}
    for name in CONFIGS:
        try:
            cfg = yaml.safe_load((Path(base) / name).read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            continue
        for kind in out:
            m = re.fullmatch(r"v?(\d+)", str(cfg.get(f"{kind}_version", "")))
            if m:
                out[kind].setdefault(int(m.group(1)), []).append(name)
    return out


def compose_system_prompt(prompt_text: str) -> tuple[str, str]:
    """Fill the rubric slot and hash the result, exactly as ``run_eval.py`` does before a run."""
    from agents.rubric import render_rubric
    text = prompt_text.replace(SLOT, render_rubric()) if SLOT in prompt_text else prompt_text
    return text, hashlib.sha256(text.encode("utf-8")).hexdigest()[:10]


def preview(base: Path, prompt_text: str, rubric: int) -> tuple[str, str]:
    """The system prompt exactly as a run would send it, plus its hash (as in results_log.csv).

    Loads ``rubric`` as the process-wide active rubric, which is what a run does too."""
    from agents.rubric import load_rubric
    path = path_for(base, "rubric", rubric)
    if not path.is_file():
        raise VersionError(f"rubric v{rubric} does not exist")
    load_rubric(path)
    return compose_system_prompt(normalize_text(prompt_text))


# ---- comparing versions ---------------------------------------------------------------

RUN_FIELDS = ("timestamp", "model", "example_set_version", "total", "verdict_accuracy",
              "criteria_exact_rate", "est_cost_usd", "report_file")


@dataclass
class Comparison:
    diff: list[str]
    added: int
    removed: int
    changed: bool


def compare(base: Path, kind: str, a: int, b: int, context: int | None = 3) -> Comparison:
    """Unified diff from version ``a`` to version ``b``. ``context=None`` shows the whole file."""
    old = normalize_text(read_version(base, kind, a)).splitlines()
    new = normalize_text(read_version(base, kind, b)).splitlines()
    n = max(len(old), len(new)) if context is None else context
    if n < 0:
        raise VersionError("context must be zero or more lines")
    diff = [line.rstrip("\n") for line in difflib.unified_diff(
        old, new, f"v{a}", f"v{b}", lineterm="", n=n)]
    added = sum(1 for l in diff if l.startswith("+") and not l.startswith("+++"))
    removed = sum(1 for l in diff if l.startswith("-") and not l.startswith("---"))
    return Comparison(diff, added, removed, old != new)


def _first_committed(path: Path) -> str:
    """When git first added ``path``. A checkout stamps every file with the time it was written
    to disk, so the file's own time says nothing about when a version was made; it is only the
    fallback for a file git does not know about (or when git is not available)."""
    import subprocess
    try:
        out = subprocess.run(
            ["git", "log", "--diff-filter=A", "--follow", "--format=%cd",
             "--date=format:%Y-%m-%d %H:%M:%S", "--", path.name],
            cwd=path.parent, capture_output=True, text=True, timeout=10, check=True).stdout.split()
        if len(out) >= 2:
            return f"{out[-2]} {out[-1]}"   # oldest add, in case the file was ever re-added
    except (OSError, subprocess.SubprocessError):
        pass
    return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")


def version_info(base: Path, kind: str, n: int) -> dict:
    """What ``versions.csv`` recorded when ``n`` was saved, plus ``created``: the logged save time,
    or for versions made before the editor, which were never logged, when git first added the
    file (its own time outside a git checkout)."""
    path = path_for(base, kind, n)   # validates kind and n
    if not path.is_file():
        raise VersionError(f"{kind} v{n} does not exist")
    log = _dir(base, kind) / "versions.csv"
    try:
        with open(log, encoding="utf-8", newline="") as f:
            rows = [r for r in csv.DictReader(f) if r.get("version") == f"v{n}"]
    except OSError:
        rows = []
    if not rows:
        return {"version": n, "logged": False, "created": _first_committed(path)}
    row = rows[-1]
    based = re.fullmatch(r"v(\d+)", row.get("based_on") or "")
    return {"version": n, "logged": True, "based_on": int(based.group(1)) if based else None,
            "saved_at": row.get("saved_at", ""), "note": row.get("note", ""),
            "created": row.get("saved_at", "")}


def runs_for(base: Path, kind: str, n: int, limit: int = 20) -> list[dict]:
    """Finished runs in ``results_log.csv`` that used this version, newest last."""
    path_for(base, kind, n)
    try:
        with open(Path(base) / "results_log.csv", encoding="utf-8-sig", newline="") as f:
            rows = [r for r in csv.DictReader(f) if r.get(f"{kind}_version") == f"v{n}"]
    except OSError:
        return []
    return [{k: r.get(k) or "" for k in RUN_FIELDS} for r in rows[-limit:]]
