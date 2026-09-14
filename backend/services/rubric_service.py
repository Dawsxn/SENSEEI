"""The rubric, as the student is allowed to see it.

`student-tutoring-loop.md` treats the criterion vocabulary as user-facing: the
student is told which criteria a response missed, so they must be able to find
out what those criteria ask for. This serves that text.

**Verbatim, never paraphrased.** What the panel shows has to be the same words
the Assessment Agent was given, or the student is reading one standard and being
graded against another. That is also why the frontend cannot hold its own copy.

Only the pinned version is served, never an arbitrary one. `load_rubric` sets the
process-wide active rubric as a side effect, so reading some other version on
request would swap the rubric the live grading uses.
"""

from __future__ import annotations

from functools import lru_cache

from agents.rubric import load_rubric

from ..agent_runtime import AGENTS_DIR
from ..settings import get_settings


@lru_cache
def pinned_rubric() -> dict:
    """The rubric this deployment grades against, grouped by step.

    Cached: it is a file read whose contents cannot change without a restart,
    since the version is a setting.
    """
    version = get_settings().rubric_version
    # Same file the agents were built from, so this re-sets the active rubric to
    # the value it already holds. Harmless here, and the reason the version is
    # not a parameter.
    rubric = load_rubric(AGENTS_DIR / "rubrics" / f"rubric_{version}.yaml")

    return {
        "version": version,
        "steps": [
            {
                "step": step,
                "criteria": [
                    {"name": name, "requirement": body.get("pass", "")}
                    for name, body in criteria.items()
                ],
            }
            for step, criteria in rubric.items()
        ],
    }
