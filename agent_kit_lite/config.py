"""Runtime configuration, validated once at startup.

Every value comes from the environment so the same build runs unchanged in
development, CI and production. Invalid values fail fast with one line per
problem instead of surfacing later as a confusing SDK error. Blank values
count as unset, so an untouched line in .env means "use the default".
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

LogLevel = Literal["debug", "info", "warn", "error"]
_LOG_LEVELS: tuple[LogLevel, ...] = ("debug", "info", "warn", "error")

CONFIG_HELP = """Environment (a .env file in the current directory is read if present):
  ANTHROPIC_API_KEY      required to run; the Agent SDK authenticates with an API key
  AGENT_MODEL            model alias or ID            default claude-opus-5-5
  AGENT_MAX_TURNS        1..200                       default 12
  AGENT_MAX_BUDGET_USD   >0 and <=100, per run        default 0.50
  NOTES_DIR              where notes.jsonl is written default ./data/notes (relative to cwd)
  LOG_LEVEL              debug|info|warn|error        default info (JSON lines on stderr)"""


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


_LINE = re.compile(r"^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")


def load_dotenv(file: str | Path = ".env", target: MutableMapping[str, str] | None = None) -> list[str]:
    """Load KEY=VALUE lines from a .env file into ``target`` (default os.environ)
    without overwriting variables that are already set. Missing file: no-op.

    Tiny on purpose: no interpolation, no multi-line values. Quotes around a
    value are stripped, ``#`` starts a comment, ``export KEY=...`` is accepted.
    Returns the names of the variables it set.
    """
    env: MutableMapping[str, str] = os.environ if target is None else target
    path = Path(file)
    if not path.exists():
        return []
    set_keys: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = _LINE.match(line)
        if not m:
            continue
        key, value = m.group(1), m.group(2).strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        elif " #" in value:
            value = value.split(" #", 1)[0].strip()
        if key not in env:
            env[key] = value
            set_keys.append(key)
    return set_keys


def _int(env: Mapping[str, str], key: str, default: int, lo: int, hi: int, problems: list[str]) -> int:
    raw = (env.get(key) or "").strip()
    if not raw:
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
    raw = (env.get(key) or "").strip()
    if not raw:
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

    api_key = (source.get("ANTHROPIC_API_KEY") or "").strip() or None
    model = (source.get("AGENT_MODEL") or "").strip() or "claude-opus-5-5"
    max_turns = _int(source, "AGENT_MAX_TURNS", 12, 1, 200, problems)
    max_budget = _float(source, "AGENT_MAX_BUDGET_USD", 0.5, 0.0, 100.0, problems)
    notes_dir = (source.get("NOTES_DIR") or "").strip() or "./data/notes"
    raw_level = (source.get("LOG_LEVEL") or "").strip() or "info"
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
    """Raise if no credential is available.

    ``run_agent()`` calls this too, because the SDK would otherwise fall back to
    whatever Claude Code login exists on the host, which Anthropic does not
    permit for third-party products.
    """
    if not config.api_key:
        raise ConfigError(
            "ANTHROPIC_API_KEY is not set. The Agent SDK needs an Anthropic API key.\n"
            "Either put ANTHROPIC_API_KEY=sk-ant-... in a .env file in the current directory,\n"
            "or export it: bash  export ANTHROPIC_API_KEY=sk-ant-...   "
            'PowerShell  $env:ANTHROPIC_API_KEY="sk-ant-..."'
        )
