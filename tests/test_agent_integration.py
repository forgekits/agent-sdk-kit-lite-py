"""Hits the real API. Costs a few cents. Runs only when both are set:
RUN_INTEGRATION=1 ANTHROPIC_API_KEY=... pytest tests/test_agent_integration.py
"""

import os
from pathlib import Path

import pytest

from agent_kit_lite.agent import run_agent
from agent_kit_lite.config import load_config
from agent_kit_lite.logger import silent_logger
from agent_kit_lite.tools.notes import NotesStore

enabled = os.environ.get("RUN_INTEGRATION") == "1" and bool(os.environ.get("ANTHROPIC_API_KEY"))


@pytest.mark.skipif(not enabled, reason="set RUN_INTEGRATION=1 and ANTHROPIC_API_KEY")
async def test_calculator_round_trip(tmp_path: Path) -> None:
    config = load_config({**os.environ, "AGENT_MAX_TURNS": "6", "AGENT_MAX_BUDGET_USD": "0.30"})
    result = await run_agent(
        "Use the calculator: what is (1200 * 1.081) / 12? Reply with the number only.",
        config,
        logger=silent_logger,
        notes_store=NotesStore(tmp_path),
    )
    assert result.summary.ok
    assert "108.1" in result.summary.text
    assert any(c.tool == "mcp__kit__calculate" for c in result.tool_calls)
    assert 0 < result.summary.cost_usd < 0.30
