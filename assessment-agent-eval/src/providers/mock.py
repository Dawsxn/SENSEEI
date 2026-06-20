"""Offline stub provider for smoke-testing the pipeline + report with no API key.

It does NOT assess anything — it always returns a fixed PASS verdict. Use it only
to confirm the CSV -> agent -> report wiring works end to end (e.g. in CI or a
first local run). Real evaluation needs gemini or openai_compat.
"""

from __future__ import annotations

import json

from .base import LLMProvider


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
        return json.dumps(
            {
                "verdict": "PASS",
                "fail_criteria": [],
                "criteria": {},
                "raw_response": "[MOCK] no real assessment performed",
            }
        )
