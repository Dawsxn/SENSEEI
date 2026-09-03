"""Offline stub provider for smoke-testing the pipeline + report with no API key.

It does NOT assess anything — it always returns a fixed PASS verdict. Use it only
to confirm the CSV -> agent -> report wiring works end to end (e.g. in CI or a
first local run). Real evaluation needs gemini or openai_compat.
"""

from __future__ import annotations

import json
import re

from .base import LLMProvider
from ..rubric import canonical_step, criteria_for


class MockProvider(LLMProvider):
    name = "mock"
    model_name = "mock"

    def __init__(self, config: dict):
        self.config = config
        self.last_usage = None
        self.last_finish_reason = None

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        # Fake usage so the cost-logging path can be smoke-tested offline.
        self.last_usage = {
            "input_tokens": 1500,
            "output_tokens": 200,
            "thinking_tokens": 0,
            "total_tokens": 1700,
        }
        self.last_finish_reason = "STOP"

        # A tutor prompt carries a SITUATION section; an assessment prompt does
        # not. The tutor wants prose, so returning the assessment JSON here would
        # be wrong. This only affects tutor prompts, which the eval never sends,
        # so the eval's mock smoke test is unchanged.
        if "# SITUATION" in user_prompt:
            return self._tutor_prose(user_prompt)

        # Emit an all-pass judgment for every criterion of the step named in the
        # user prompt, so the derive-verdict path is exercised end to end offline.
        m = re.search(r"#\s*CURRENT SEE-I STEP\s*\n\s*(.+)", user_prompt)
        step = canonical_step(m.group(1).strip()) if m else None
        criteria = {
            c: {"pass": True, "reason": "[MOCK] always passes"}
            for c in (criteria_for(step) if step else [])
        }
        return json.dumps(
            {
                "verdict": "PASS",
                "fail_criteria": [],
                "criteria": criteria,
                "raw_response": "[MOCK] no real assessment performed",
            }
        )

    @staticmethod
    def _tutor_prose(user_prompt: str) -> str:
        m = re.search(r"#\s*CURRENT SEE-I STEP\s*\n\s*(.+)", user_prompt)
        step = m.group(1).strip() if m else "this step"
        s = re.search(r"#\s*SITUATION\s*\n\s*(.+)", user_prompt)
        situation = s.group(1).strip() if s else ""
        return f"[MOCK tutor] {step}. {situation[:80]}"

    def stream(self, system_prompt: str, user_prompt: str):
        """Yield the mock answer in word-sized pieces, so streaming is exercised.

        Usage and finish reason are set the same way `complete()` sets them, so a
        streamed tutor turn still records its (fake) token counts offline.
        """
        text = self.complete(system_prompt, user_prompt)
        words = text.split(" ")
        for i, word in enumerate(words):
            yield word if i == 0 else " " + word
