"""A small, tested starting point for building agents on the Claude Agent SDK."""

from .agent import (
    DEFAULT_SYSTEM_PROMPT,
    SERVER_KEY,
    RunResult,
    ToolCallRecord,
    build_options,
    create_kit_server,
    run_agent,
)
from .config import AgentConfig, ConfigError, load_config, require_api_key
from .logger import Logger, create_logger, silent_logger
from .report import RunSummary, explain_failure, format_summary, summarize_result
from .tools.calculator import CalculatorError, calculate_tool, evaluate
from .tools.notes import MAX_BODY_CHARS, Note, NotesStore, create_notes_tools

__all__ = [
    "DEFAULT_SYSTEM_PROMPT",
    "MAX_BODY_CHARS",
    "SERVER_KEY",
    "AgentConfig",
    "CalculatorError",
    "ConfigError",
    "Logger",
    "Note",
    "NotesStore",
    "RunResult",
    "RunSummary",
    "ToolCallRecord",
    "build_options",
    "calculate_tool",
    "create_kit_server",
    "create_logger",
    "create_notes_tools",
    "evaluate",
    "explain_failure",
    "format_summary",
    "load_config",
    "require_api_key",
    "run_agent",
    "silent_logger",
    "summarize_result",
]
