"""Canonical SEE-I rubric data.

This module is the code's source of truth for the *names* of the rubric criteria
per SEE-I step. It is used to validate the agent's JSON output and to build the
per-criterion stats in the report.

The human-editable copy of the rubric that is actually sent to the model lives in
the versioned system prompt (prompts/system_prompt_vN.md). When you change a
criterion there, mirror the name here so validation/stats stay aligned.
"""

from __future__ import annotations

# step -> {criterion_name: {"pass": ..., "fail": ...}}
RUBRIC: dict[str, dict[str, dict[str, str]]] = {
    "State": {
        "Length": {
            "pass": "Exactly 1 or 2 complete sentences.",
            "fail": "3 or more sentences, or incomplete fragments.",
        },
        "Originality": {
            "pass": "Uses no more than 3 consecutive words directly from the text "
                    "(excluding specific technical terms or proper nouns).",
            "fail": "Copies entire clauses or sentences directly from the source text.",
        },
        "Scope": {
            "pass": "States an active relationship, process, or main theme.",
            "fail": "States a static fact, statistic, or date.",
        },
        "Clarity": {
            "pass": "Subjects are explicitly named.",
            "fail": "Starts with ambiguous pronouns (e.g., 'It is when...', 'This happens because...').",
        },
        "Accuracy": {
            "pass": "Does not contradict the core premise of the text.",
            "fail": "Reverses a relationship, states something factually incorrect, "
                    "or is unrelated to the text.",
        },
    },
    "Elaborate": {
        "Expansion": {
            "pass": "Introduces the How, Why, or When of the concept stated in the State step.",
            "fail": "Merely paraphrases the State step without adding new mechanisms.",
        },
        "Jargon Translation": {
            "pass": "Defines or uses plain language to explain technical terms.",
            "fail": "Relies on technical jargon without defining what it means.",
        },
        "Relationship Accuracy": {
            "pass": "Accurately identifies cause/effect, part/whole, or chronological steps.",
            "fail": "Claims a cause/effect that the text does not support.",
        },
        "Focus": {
            "pass": "All details directly serve to explain the central concept.",
            "fail": "Includes tangents, trivia, or sub-topics unrelated to the central concept.",
        },
    },
    "Exemplify": {
        "Originality": {
            "pass": "Provides an example not explicitly mentioned in the source text.",
            "fail": "Reuses an example provided by the author of the text.",
        },
        "Concreteness": {
            "pass": "Points to a specific, named entity, event, or real-world instance.",
            "fail": "Uses vague hypotheticals or broad categories.",
        },
        "Explicit Mapping": {
            "pass": "Explicitly connects a feature of the example to a feature of the concept.",
            "fail": "Drops the example without explaining how it shows the concept.",
        },
    },
    "Illustrate": {
        "Cross-Domain": {
            "pass": "Compares the concept to a completely different field, discipline, or everyday life.",
            "fail": "Provides another literal example from the exact same field/domain.",
        },
        "Structural Match": {
            "pass": "The relationship between parts in the analogy matches the relationship in the concept.",
            "fail": "Shares only a superficial trait; the underlying mechanism fails to match.",
        },
        "Format": {
            "pass": "Is a written metaphor / simile / analogy.",
            "fail": "Is literally just text restating the elaboration, with no metaphor or analogy.",
        },
    },
}

STEPS = list(RUBRIC.keys())


def criteria_for(step: str) -> list[str]:
    """Canonical criterion names for a step (raises KeyError on unknown step)."""
    return list(RUBRIC[step].keys())


def normalize(name: str) -> str:
    """Loose key for case/space/hyphen-insensitive matching."""
    return " ".join(name.strip().lower().replace("-", " ").replace("_", " ").split())


def canonical_step(step: str) -> str | None:
    """Map a possibly-messy step name to the canonical one, or None if unknown."""
    target = normalize(step)
    for s in STEPS:
        if normalize(s) == target:
            return s
    return None


def canonical_criterion(step: str, name: str) -> str | None:
    """Map a possibly-messy criterion name to the canonical one for a step, else None."""
    cs = canonical_step(step)
    if cs is None:
        return None
    target = normalize(name)
    for c in RUBRIC[cs]:
        if normalize(c) == target:
            return c
    return None
