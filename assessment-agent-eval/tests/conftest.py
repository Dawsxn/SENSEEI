"""Tests for the eval folder's own code (the prompt editor). Run from the repo root:

    pytest assessment-agent-eval/tests

They are separate from the backend suite in ``tests/`` and need no database or API key.
"""

import shutil
import sys
from pathlib import Path

import pytest

EVAL = Path(__file__).resolve().parents[1]
REPO = EVAL.parent
for p in (str(EVAL), str(REPO)):   # `src` (this folder) and `agents` (beside it)
    if p not in sys.path:
        sys.path.insert(0, p)

# Copied into a throwaway repo layout, so a test can never write into the real agents/ folder.
FILES = {
    "agents/prompts/system_prompt_v3.md": REPO / "agents/prompts/system_prompt_v3.md",
    "agents/prompts/tutor_prompt_v2.md": REPO / "agents/prompts/tutor_prompt_v2.md",
    "agents/rubrics/rubric_v3.yaml": REPO / "agents/rubrics/rubric_v3.yaml",
    "assessment-agent-eval/config.yaml": EVAL / "config.yaml",
    "assessment-agent-eval/data/example_set_v3.csv": EVAL / "data/example_set_v3.csv",
}


@pytest.fixture
def base(tmp_path):
    """A copy of the files the editor works with; returns the eval folder inside it."""
    for rel, src in FILES.items():
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, tmp_path / rel)
    return tmp_path / "assessment-agent-eval"


@pytest.fixture
def restore_rubric():
    """Preview loads a rubric process-wide, as a run does; put the shipped one back afterwards."""
    yield
    from agents.rubric import load_rubric
    load_rubric(REPO / "agents/rubrics/rubric_v3.yaml")
