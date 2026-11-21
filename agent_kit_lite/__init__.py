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
from .config import CONFIG_HELP, AgentConfig, ConfigError, load_config, load_dotenv, require_api_key
from .logger import Logger, create_logger, silent_logger
from .report import RunSummary, explain_failure, format_summary, status_label, summarize_result
from .tools.calculator import CalculatorError, calculate_tool, evaluate
from .tools.notes import MAX_BODY_CHARS, Note, NotesStore, create_notes_tools

__all__ = [
    "DEFAULT_SYSTEM_PROMPT",
    "MAX_BODY_CHARS",
    "SERVER_KEY",
    "CONFIG_HELP",
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
    "load_dotenv",
    "require_api_key",
    "run_agent",
    "silent_logger",
    "status_label",
    "summarize_result",
]
