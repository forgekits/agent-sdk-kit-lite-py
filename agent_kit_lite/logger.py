"""Minimal structured logger: one JSON object per line on stderr.

stderr keeps logs apart from the agent's answer on stdout, so the CLI can be
piped. Swap it for structlog or your platform logger when you embed the kit.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .config import LogLevel

_ORDER: dict[str, int] = {"debug": 10, "info": 20, "warn": 30, "error": 40}


def _stderr_sink(line: str) -> None:
    sys.stderr.write(line + "\n")


@dataclass
class Logger:
    level: LogLevel = "info"
    sink: Callable[[str], None] = field(default=_stderr_sink)

    def _emit(self, level: str, msg: str, fields: dict[str, Any] | None) -> None:
        if _ORDER[level] < _ORDER[self.level]:
            return
        record: dict[str, Any] = {"ts": datetime.now(timezone.utc).isoformat(), "level": level, "msg": msg}
        if fields:
            record.update(fields)
        self.sink(json.dumps(record, default=str))

    def debug(self, msg: str, **fields: Any) -> None:
        self._emit("debug", msg, fields)

    def info(self, msg: str, **fields: Any) -> None:
        self._emit("info", msg, fields)

    def warn(self, msg: str, **fields: Any) -> None:
        self._emit("warn", msg, fields)

    def error(self, msg: str, **fields: Any) -> None:
        self._emit("error", msg, fields)


def create_logger(level: LogLevel = "info", sink: Callable[[str], None] | None = None) -> Logger:
    return Logger(level=level, sink=sink or _stderr_sink)


silent_logger = Logger(level="error", sink=lambda _line: None)
"""A logger that records nothing. Handy in tests."""
