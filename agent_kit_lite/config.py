"""Runtime configuration, validated once at startup.

Every value comes from the environment so the same build runs unchanged in
development, CI and production. Invalid values fail fast with one line per
problem instead of surfacing later as a confusing SDK error.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

LogLevel = Literal["debug", "info", "warn", "error"]
_LOG_LEVELS: tuple[LogLevel, ...] = ("debug", "info", "warn", "error")


class ConfigError(Exception):
    """Raised when the environment holds an invalid value."""


@dataclass(frozen=True)
class AgentConfig:
    api_key: str | None
    model: str
    max_turns: int
    max_budget_usd: float
    notes_dir: str
    log_level: LogLevel


def _int(env: Mapping[str, str], key: str, default: int, lo: int, hi: int, problems: list[str]) -> int:
    raw = env.get(key)
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except ValueError:
        problems.append(f"{key}: expected an integer, got {raw!r}")
        return default
    if not lo <= value <= hi:
        problems.append(f"{key}: must be between {lo} and {hi}, got {value}")
    return value


def _float(
    env: Mapping[str, str], key: str, default: float, lo: float, hi: float, problems: list[str]
) -> float:
    raw = env.get(key)
    if raw is None or raw == "":
        return default
    try:
        value = float(raw)
    except ValueError:
        problems.append(f"{key}: expected a number, got {raw!r}")
        return default
    if not lo < value <= hi:
        problems.append(f"{key}: must be greater than {lo} and at most {hi}, got {value}")
    return value


def load_config(env: Mapping[str, str] | None = None) -> AgentConfig:
    """Parse configuration from an environment mapping (defaults to os.environ).

    Raises ConfigError listing every invalid variable.
    """
    source: Mapping[str, str] = os.environ if env is None else env
    problems: list[str] = []

    api_key = source.get("ANTHROPIC_API_KEY") or None
    model = source.get("AGENT_MODEL") or "claude-opus-5-5"
    max_turns = _int(source, "AGENT_MAX_TURNS", 12, 1, 200, problems)
    max_budget = _float(source, "AGENT_MAX_BUDGET_USD", 0.5, 0.0, 100.0, problems)
    notes_dir = source.get("NOTES_DIR") or "./data/notes"
    raw_level = source.get("LOG_LEVEL") or "info"
    if raw_level not in _LOG_LEVELS:
        problems.append(f"LOG_LEVEL: must be one of {', '.join(_LOG_LEVELS)}, got {raw_level!r}")
        raw_level = "info"

    if problems:
        raise ConfigError("Invalid configuration:\n  " + "\n  ".join(problems))

    return AgentConfig(
        api_key=api_key,
        model=model,
        max_turns=max_turns,
        max_budget_usd=max_budget,
        notes_dir=notes_dir,
        log_level=raw_level,  # type: ignore[arg-type]
    )


def require_api_key(config: AgentConfig) -> None:
    """Raise if no credential is available. The CLI calls this; the library does not."""
    if not config.api_key:
        raise ConfigError(
            "ANTHROPIC_API_KEY is not set. The Agent SDK needs an Anthropic API key; "
            "copy .env.example to .env and fill it in."
        )
