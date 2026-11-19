from pathlib import Path

from agent_kit_lite.agent import (
    SERVER_KEY,
    ToolCallRecord,
    build_options,
    create_audit_hook,
    create_kit_server,
)
from agent_kit_lite.config import load_config
from agent_kit_lite.logger import silent_logger
from agent_kit_lite.tools.notes import NotesStore


def test_build_options_locks_down(tmp_path: Path) -> None:
    config = load_config(
        {"AGENT_MAX_TURNS": "5", "AGENT_MAX_BUDGET_USD": "0.25", "ANTHROPIC_API_KEY": "test-key"}
    )
    server = create_kit_server(NotesStore(tmp_path))
    options = build_options(config, server, [])

    assert options.tools == []  # no built-in tools
    assert options.allowed_tools == [f"mcp__{SERVER_KEY}__*"]
    assert options.permission_mode == "dontAsk"
    assert options.setting_sources == []
    assert options.max_turns == 5
    assert options.max_budget_usd == 0.25
    assert options.model == "claude-opus-5-5"
    assert options.env["ANTHROPIC_API_KEY"] == "test-key"
    assert list(options.mcp_servers.keys()) == [SERVER_KEY]
    assert options.hooks is not None
    assert options.hooks["PreToolUse"][0].matcher == f"^mcp__{SERVER_KEY}__"


def test_kit_server_exposes_three_tools(tmp_path: Path) -> None:
    server = create_kit_server(NotesStore(tmp_path))
    # The SDK returns a config dict with an in-process MCP server instance.
    assert isinstance(server, dict)
    assert server.get("type") == "sdk"
    assert server.get("name") == "agent-sdk-kit"


async def test_audit_hook_records_and_allows() -> None:
    sink: list[ToolCallRecord] = []
    hook = create_audit_hook(silent_logger, sink)
    out = await hook(
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "mcp__kit__calculate",
            "tool_input": {"expression": "1+1"},
        },
        "tu1",
        None,
    )
    assert out == {}
    assert len(sink) == 1
    assert sink[0].tool == "mcp__kit__calculate"


async def test_audit_hook_ignores_other_events() -> None:
    sink: list[ToolCallRecord] = []
    hook = create_audit_hook(silent_logger, sink)
    assert await hook({"hook_event_name": "Stop"}, None, None) == {}
    assert sink == []
