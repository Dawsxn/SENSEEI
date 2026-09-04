"""Build the two agents the way the running app needs them.

The eval and scripts/session.py both wire up an Assessment Agent and a Tutor
Agent by hand. This does the same from `backend.settings`, so the backend runs
the same agent code against the same prompts and rubric, with the provider,
model and versions coming from configuration rather than command-line flags.

The pair is cached: the prompts and rubric are read once, and the provider
clients are reused across requests rather than rebuilt per turn.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

import agents as agents_pkg
from agents.assessment import AssessmentAgent
from agents.providers import get_provider
from agents.rubric import load_rubric, render_rubric
from agents.tutor import TutorAgent

from .settings import Settings, get_settings

AGENTS_DIR = Path(agents_pkg.__file__).resolve().parent


@dataclass
class Agents:
    assessor: AssessmentAgent
    tutor: TutorAgent


def _prompt(name: str) -> str:
    return (AGENTS_DIR / "prompts" / name).read_text(encoding="utf-8")


def build_agents(settings: Settings) -> Agents:
    """Construct both agents from settings. Loads the rubric as a side effect.

    `load_rubric` populates the module-level rubric that `criteria_for` and the
    prompt rendering read, so it must run before the prompts are rendered and
    before any assessment is parsed.
    """
    # A real provider reads its API key from os.environ (the key name is a
    # setting; the key value never sits in a config dict). pydantic-settings
    # reads .env into the Settings object but not into os.environ, so load it
    # here too, or a real provider cannot find its key. Does not override a
    # variable already set by the host, which is how deployments supply it.
    load_dotenv(AGENTS_DIR.parent / ".env")

    load_rubric(AGENTS_DIR / "rubrics" / f"rubric_{settings.rubric_version}.yaml")
    rubric_block = render_rubric()

    assess_prompt = _prompt(
        f"system_prompt_{settings.assessment_prompt_version}.md"
    ).replace("{{RUBRIC}}", rubric_block)
    tutor_prompt = _prompt(
        f"tutor_prompt_{settings.tutor_prompt_version}.md"
    ).replace("{{RUBRIC}}", rubric_block)

    base = settings.provider_config()
    # The Assessment Agent returns JSON; the Tutor Agent returns prose.
    assessor = AssessmentAgent(get_provider({**base, "json_mode": True}), assess_prompt)
    tutor = TutorAgent(get_provider({**base, "json_mode": False}), tutor_prompt)
    return Agents(assessor=assessor, tutor=tutor)


@lru_cache
def get_agents() -> Agents:
    """The process-wide agent pair, built once from the active settings."""
    return build_agents(get_settings())
