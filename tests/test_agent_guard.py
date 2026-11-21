from pathlib import Path
from types import SimpleNamespace

import pytest

from agent_kit_lite.agent import create_kit_server, run_agent
from agent_kit_lite.config import ConfigError, load_config
from agent_kit_lite.logger import silent_logger
from agent_kit_lite.report import explain_failure, format_summary, summarize_result
from agent_kit_lite.tools.notes import NotesStore


async def test_run_agent_refuses_without_key() -> None:
    with pytest.raises(ConfigError, match="ANTHROPIC_API_KEY"):
        await run_agent("hi", load_config({}), logger=silent_logger)


def test_extra_tools_are_served(tmp_path: Path) -> None:
    from typing import Any

    from claude_agent_sdk import tool

    @tool("ping", "Ping", {"type": "object", "properties": {}})
    async def ping(args: dict[str, Any]) -> dict[str, Any]:
        return {"content": [{"type": "text", "text": "pong"}]}

    server = create_kit_server(NotesStore(tmp_path), [ping])
    assert server["type"] == "sdk"
    assert server["name"] == "agent-sdk-kit"


def test_sdk_error_result_is_a_failure() -> None:
    msg = SimpleNamespace(
        subtype="success",
        is_error=True,
        result="Invalid API key · Fix external API key",
        num_turns=1,
        duration_ms=300,
        duration_api_ms=0,
        total_cost_usd=0.0,
        usage=None,
        model_usage=None,
        permission_denials=None,
        errors=None,
        session_id="s",
    )
    s = summarize_result(msg)
    assert s.ok is False
    assert s.text == ""
    assert s.errors == ("Invalid API key · Fix external API key",)
    assert "status      failed (sdk error)" in format_summary(s)
    assert "Invalid API key" in (explain_failure(s) or "")
