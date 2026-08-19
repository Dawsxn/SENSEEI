"""SENSEEI's LLM-backed agents — shared by the eval harness and the backend.

This package holds the agents themselves, not the scaffolding around them: the
Assessment Agent (:mod:`agents.assessment`), the rubric it grades against
(:mod:`agents.rubric`), the swappable provider backends
(:mod:`agents.providers`), and their versioned assets (``prompts/``,
``rubrics/``).

It lives at the repo root, outside ``assessment-agent-eval/``, so the eval and
the backend import the *same* code. That is what lets the eval's measured
pedagogical alignment say anything about the agent that actually ships.

Resolve the bundled assets against the installed package rather than the
current working directory::

    import agents
    AGENTS = Path(agents.__file__).resolve().parent
    rubric_path = AGENTS / "rubrics" / "rubric_v3.yaml"
"""
