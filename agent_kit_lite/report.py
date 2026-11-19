"""Flatten the SDK's ResultMessage into a serialisable summary.

``cost_usd`` is the SDK's local estimate, not a billing statement. The
per-model breakdown comes from ``model_usage``; ``usage`` covers only the
main loop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ModelCost:
    cost_usd: float
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class RunSummary:
    ok: bool
    subtype: str
    text: str
    errors: tuple[str, ...]
    turns: int
    duration_ms: int
    api_ms: int
    cost_usd: float
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int
    models: dict[str, ModelCost] = field(default_factory=dict)
    permission_denials: int = 0
    session_id: str = ""


def _get(obj: Any, *names: str, default: Any = None) -> Any:
    """Read the first present attribute or key among ``names`` (camelCase or snake_case)."""
    for name in names:
        if isinstance(obj, dict):
            if name in obj and obj[name] is not None:
                return obj[name]
        elif hasattr(obj, name) and getattr(obj, name) is not None:
            return getattr(obj, name)
    return default


def summarize_result(msg: Any) -> RunSummary:
    """Accepts a ``ResultMessage`` (or any object with the same fields)."""
    usage = _get(msg, "usage", default={}) or {}
    models: dict[str, ModelCost] = {}
    for name, u in (_get(msg, "model_usage", "modelUsage", default={}) or {}).items():
        models[name] = ModelCost(
            cost_usd=float(_get(u, "costUSD", "cost_usd", default=0.0)),
            input_tokens=int(_get(u, "inputTokens", "input_tokens", default=0)),
            output_tokens=int(_get(u, "outputTokens", "output_tokens", default=0)),
        )
    subtype = str(_get(msg, "subtype", default="unknown"))
    is_error = bool(_get(msg, "is_error", default=False))
    result_text = _get(msg, "result", default="") or ""
    errors = tuple(str(e) for e in (_get(msg, "errors", default=None) or []))
    ok = subtype == "success" and not is_error
    errs = errors if errors else (() if subtype == "success" else (subtype,))
    return RunSummary(
        ok=ok,
        subtype=subtype,
        text=str(result_text) if ok else "",
        errors=errs,
        turns=int(_get(msg, "num_turns", default=0)),
        duration_ms=int(_get(msg, "duration_ms", default=0)),
        api_ms=int(_get(msg, "duration_api_ms", default=0)),
        cost_usd=float(_get(msg, "total_cost_usd", default=0.0) or 0.0),
        input_tokens=int(_get(usage, "input_tokens", default=0)),
        output_tokens=int(_get(usage, "output_tokens", default=0)),
        cache_read_tokens=int(_get(usage, "cache_read_input_tokens", default=0)),
        cache_write_tokens=int(_get(usage, "cache_creation_input_tokens", default=0)),
        models=models,
        permission_denials=len(_get(msg, "permission_denials", default=None) or []),
        session_id=str(_get(msg, "session_id", default="")),
    )


def _money(value: float) -> str:
    return f"${value:.4f}"


def format_summary(s: RunSummary) -> str:
    """Human-readable multi-line report for terminals and logs."""
    lines = [
        f"status      {'ok' if s.ok else 'failed'} ({s.subtype})",
        f"turns       {s.turns}",
        f"duration    {s.duration_ms / 1000:.1f}s total, {s.api_ms / 1000:.1f}s in API",
        f"cost        {_money(s.cost_usd)} (local estimate)",
        f"tokens      in {s.input_tokens}, out {s.output_tokens}, "
        f"cache read {s.cache_read_tokens}, cache write {s.cache_write_tokens}",
    ]
    for name, m in s.models.items():
        lines.append(f"model       {name}: {_money(m.cost_usd)}, in {m.input_tokens}, out {m.output_tokens}")
    if s.permission_denials:
        lines.append(f"denials     {s.permission_denials}")
    if s.errors:
        lines.append(f"errors      {'; '.join(s.errors)}")
    return "\n".join(lines)


def explain_failure(s: RunSummary) -> str | None:
    """One sentence an operator can act on, or None for a clean success."""
    if s.subtype == "success":
        return None if s.ok else "The run finished but the SDK flagged an error."
    if s.subtype == "error_max_turns":
        return f"Stopped after {s.turns} turns (AGENT_MAX_TURNS). Raise the limit or narrow the task."
    if s.subtype == "error_max_budget_usd":
        return f"Stopped at {_money(s.cost_usd)} (AGENT_MAX_BUDGET_USD). Raise the budget or narrow the task."
    if s.subtype == "error_max_structured_output_retries":
        return "The model could not produce valid structured output after the allowed retries."
    if s.subtype == "error_during_execution":
        return f"Execution error: {'; '.join(s.errors) or 'no details'}."
    return f"Run ended with {s.subtype}."
