"""Run one prompt through a locked-down Claude Agent SDK query."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    HookMatcher,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ToolUseBlock,
    create_sdk_mcp_server,
    query,
)

from .config import AgentConfig, require_api_key
from .logger import Logger, create_logger
from .report import RunSummary, summarize_result
from .tools.calculator import calculate_tool
from .tools.notes import NotesStore, create_notes_tools

SERVER_KEY = "kit"
"""Key under which the in-process MCP server is registered. Tool names become mcp__kit__<name>."""

DEFAULT_SYSTEM_PROMPT = (
    "You are a careful assistant embedded in an application. "
    "Use the calculate tool for any arithmetic; never compute numbers in your head. "
    "Use save_note when the user asks you to remember something, and search_notes to recall it. "
    "Answer briefly and state when you could not complete a request."
)


@dataclass(frozen=True)
class ToolCallRecord:
    tool: str
    input: Any
    at: str


@dataclass
class RunResult:
    summary: RunSummary
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    raw: Any = None


def create_kit_server(store: NotesStore, extra_tools: Sequence[Any] = ()) -> Any:
    """Build the in-process MCP server with the kit's tools plus any of your own ``@tool`` functions."""
    return create_sdk_mcp_server(
        name="agent-sdk-kit",
        version="0.1.0",
        tools=[calculate_tool, *create_notes_tools(store), *extra_tools],
    )


def create_audit_hook(logger: Logger, sink: list[ToolCallRecord]) -> Callable[..., Any]:
    """PreToolUse hook that records every tool call and never blocks.

    Blocking policies (allow lists, argument checks, confirmations) belong in a
    hook exactly like this one: return ``hookSpecificOutput`` with
    ``permissionDecision: "deny"`` to stop a call.
    """

    async def audit(input_data: dict[str, Any], tool_use_id: str | None, context: Any) -> dict[str, Any]:
        if input_data.get("hook_event_name") != "PreToolUse":
            return {}
        record = ToolCallRecord(
            tool=str(input_data.get("tool_name")),
            input=input_data.get("tool_input"),
            at=datetime.now(timezone.utc).isoformat(),
        )
        sink.append(record)
        logger.info("tool call", tool=record.tool, input=record.input)
        return {}

    return audit


def build_options(
    config: AgentConfig,
    server: Any,
    hooks: list[Callable[..., Any]],
    system_prompt: str | None = None,
) -> ClaudeAgentOptions:
    """Assemble the SDK options for one run. Testable without calling the API."""
    env: dict[str, str] = {}
    if config.api_key:
        env["ANTHROPIC_API_KEY"] = config.api_key
    env.setdefault("CLAUDE_AGENT_SDK_CLIENT_APP", "agent-sdk-kit-lite")
    return ClaudeAgentOptions(
        model=config.model,
        system_prompt=system_prompt or DEFAULT_SYSTEM_PROMPT,
        # Remove every built-in tool (Bash, Read, Write, ...). Claude only gets our MCP tools.
        tools=[],
        mcp_servers={SERVER_KEY: server},
        # Pre-approve our tools; anything else is denied instead of waiting for a prompt.
        allowed_tools=[f"mcp__{SERVER_KEY}__*"],
        permission_mode="dontAsk",
        max_turns=config.max_turns,
        max_budget_usd=config.max_budget_usd,
        # Do not load ~/.claude or .claude settings from the machine the agent runs on.
        setting_sources=[],
        hooks={"PreToolUse": [HookMatcher(matcher=f"^mcp__{SERVER_KEY}__", hooks=hooks)]},
        env=env,
    )


async def run_agent(
    prompt: str,
    config: AgentConfig,
    *,
    logger: Logger | None = None,
    system_prompt: str | None = None,
    on_text: Callable[[str], object] | None = None,
    notes_store: NotesStore | None = None,
    extra_tools: Sequence[Any] = (),
    allow_host_credentials: bool = False,
) -> RunResult:
    """Run one prompt and return the summary.

    A single-shot ``query()`` raises ``ResultError`` after yielding an error
    result. We keep the last result message so the caller always gets a
    summary when one exists.

    Without ``ANTHROPIC_API_KEY`` the SDK would use whatever Claude Code login
    exists on the host, which Anthropic does not permit for third-party
    products, so the key is required unless ``allow_host_credentials`` is set
    (local experiments only).
    """
    if not allow_host_credentials:
        require_api_key(config)
    log = logger or create_logger(config.log_level)
    store = notes_store or NotesStore(config.notes_dir)
    server = create_kit_server(store, extra_tools)
    tool_calls: list[ToolCallRecord] = []
    options = build_options(config, server, [create_audit_hook(log, tool_calls)], system_prompt)

    log.info(
        "run start", model=config.model, max_turns=config.max_turns, max_budget_usd=config.max_budget_usd
    )
    result: ResultMessage | None = None
    try:
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, SystemMessage) and message.subtype == "init":
                log.debug(
                    "session init", data={k: message.data.get(k) for k in ("model", "tools", "mcp_servers")}
                )
            elif isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock) and on_text:
                        on_text(block.text)
                    elif isinstance(block, ToolUseBlock):
                        log.debug("assistant requests tool", tool=block.name)
            elif isinstance(message, ResultMessage):
                result = message
    except Exception as exc:  # noqa: BLE001 - ResultError after an error result is expected
        if result is None:
            raise
        log.warn("query raised after yielding a result", error=str(exc))
    if result is None:
        raise RuntimeError("The query ended without a result message")

    summary = summarize_result(result)
    log.info(
        "run end", ok=summary.ok, subtype=summary.subtype, cost_usd=summary.cost_usd, turns=summary.turns
    )
    return RunResult(summary=summary, tool_calls=tool_calls, raw=result)
