"""Load + query the versioned SEE-I rubric (single source of truth).

The rubric lives in ``rubric/rubric_vN.yaml``. Code reads the criterion NAMES
(the YAML keys) to validate the agent's output and to build the per-criterion
stats; the runner also renders the PASS conditions into the system prompt's
``{{RUBRIC}}`` placeholder, so the model and the code always use the same rubric.

Call :func:`load_rubric` once at startup (the runner does this from the
config-pinned version). All query functions operate on the loaded rubric.

Schema (v2+): pass-only. Each criterion maps to ``{"pass": "<condition>"}``.
Older rubrics may also carry a ``fail`` key; it is ignored by the code and only
kept in the YAML as a historical record.
"""

from __future__ import annotations

from pathlib import Path

# Active rubric, populated by load_rubric():  step -> {criterion: {"pass": str, ...}}
_RUBRIC: dict[str, dict[str, dict]] = {}


def load_rubric(path) -> dict:
    """Load a rubric YAML file and make it the active rubric. Returns the dict."""
    import yaml

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    norm: dict[str, dict[str, dict]] = {}
    for step, crits in data.items():
        if not isinstance(crits, dict):
            raise ValueError(f"Rubric step {step!r} must map to criteria, got {type(crits)}")
        norm[step] = {}
        for cname, cval in crits.items():
            # tolerate a bare string value (treated as the pass condition)
            norm[step][cname] = cval if isinstance(cval, dict) else {"pass": str(cval)}
    if not norm:
        raise ValueError(f"Rubric at {path} is empty")
    set_rubric(norm)
    return norm


def set_rubric(rubric: dict) -> None:
    """Set the active rubric directly (used by load_rubric and by tests)."""
    global _RUBRIC
    _RUBRIC = rubric


def _active() -> dict:
    if not _RUBRIC:
        raise RuntimeError("Rubric not loaded — call load_rubric(path) first.")
    return _RUBRIC


def steps() -> list[str]:
    """Canonical SEE-I step names, in rubric order."""
    return list(_active().keys())


def criteria_for(step: str) -> list[str]:
    """Canonical criterion names for a step (raises KeyError on unknown step)."""
    return list(_active()[step].keys())


def normalize(name: str) -> str:
    """Loose key for case/space/hyphen-insensitive matching."""
    return " ".join(name.strip().lower().replace("-", " ").replace("_", " ").split())


def canonical_step(step: str) -> str | None:
    """Map a possibly-messy step name to the canonical one, or None if unknown."""
    target = normalize(step)
    for s in _active():
        if normalize(s) == target:
            return s
    return None


def canonical_criterion(step: str, name: str) -> str | None:
    """Map a possibly-messy criterion name to the canonical one for a step, else None."""
    cs = canonical_step(step)
    if cs is None:
        return None
    target = normalize(name)
    for c in _active()[cs]:
        if normalize(c) == target:
            return c
    return None


def render_rubric() -> str:
    """Render the active rubric as Markdown tables for the prompt {{RUBRIC}} slot."""
    lines: list[str] = []
    for step in _active():
        lines.append(f"### {step.upper()}")
        lines.append("| Criterion | The response PASSES this criterion if... |")
        lines.append("|---|---|")
        for cname, cval in _active()[step].items():
            passtxt = str(cval.get("pass", "")).replace("\n", " ").strip()
            lines.append(f"| {cname} | {passtxt} |")
        lines.append("")  # blank line between steps
    return "\n".join(lines).strip()
