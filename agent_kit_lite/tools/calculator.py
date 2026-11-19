"""A safe arithmetic evaluator.

Why not ``eval``? Because the expression comes from the model, and the model
can be steered by whatever text it has read. This is a tiny recursive-descent
parser that accepts numbers, + - * / % ^, parentheses and unary minus, and
nothing else.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from claude_agent_sdk import ToolAnnotations, tool

MAX_EXPRESSION_CHARS = 500


class CalculatorError(Exception):
    """Raised for any malformed or unsafe expression."""


@dataclass(frozen=True)
class _Tok:
    kind: str  # "num" | "op" | "lparen" | "rparen"
    value: float | str | None = None


_OPS = set("+-*/%^")


def _tokenize(text: str) -> list[_Tok]:
    tokens: list[_Tok] = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch in " \t\n":
            i += 1
            continue
        if ch.isdigit() or ch == ".":
            j = i
            while j < n and (text[j].isdigit() or text[j] in "._"):
                j += 1
            raw = text[i:j].replace("_", "")
            if raw == "." or raw.count(".") > 1:
                raise CalculatorError(f'Invalid number "{raw}" at position {i}')
            try:
                value = float(raw)
            except ValueError as exc:
                raise CalculatorError(f'Invalid number "{raw}" at position {i}') from exc
            tokens.append(_Tok("num", value))
            i = j
            continue
        if ch in _OPS:
            tokens.append(_Tok("op", ch))
            i += 1
            continue
        if ch == "(":
            tokens.append(_Tok("lparen"))
            i += 1
            continue
        if ch == ")":
            tokens.append(_Tok("rparen"))
            i += 1
            continue
        raise CalculatorError(f'Unexpected character "{ch}" at position {i}')
    return tokens


class _Parser:
    def __init__(self, tokens: list[_Tok]) -> None:
        self.tokens = tokens
        self.pos = 0

    def parse(self) -> float:
        if not self.tokens:
            raise CalculatorError("Empty expression")
        value = self._additive()
        if self.pos < len(self.tokens):
            raise CalculatorError("Unexpected token after end of expression")
        return value

    def _peek(self) -> _Tok | None:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _next(self) -> _Tok:
        tok = self._peek()
        if tok is None:
            raise CalculatorError("Unexpected end of expression")
        self.pos += 1
        return tok

    def _additive(self) -> float:
        left = self._multiplicative()
        while True:
            tok = self._peek()
            if tok is not None and tok.kind == "op" and tok.value in ("+", "-"):
                self.pos += 1
                right = self._multiplicative()
                left = left + right if tok.value == "+" else left - right
            else:
                return left

    def _multiplicative(self) -> float:
        left = self._power()
        while True:
            tok = self._peek()
            if tok is not None and tok.kind == "op" and tok.value in ("*", "/", "%"):
                self.pos += 1
                right = self._power()
                if tok.value in ("/", "%") and right == 0:
                    raise CalculatorError("Division by zero")
                if tok.value == "*":
                    left = left * right
                elif tok.value == "/":
                    left = left / right
                else:
                    left = math.fmod(left, right)
            else:
                return left

    def _power(self) -> float:
        base = self._unary()
        tok = self._peek()
        if tok is not None and tok.kind == "op" and tok.value == "^":
            self.pos += 1
            exponent = self._power()  # right-associative
            try:
                return float(base**exponent)
            except OverflowError as exc:
                raise CalculatorError("Result is not a finite number") from exc
        return base

    def _unary(self) -> float:
        tok = self._peek()
        if tok is not None and tok.kind == "op" and tok.value == "-":
            self.pos += 1
            return -self._unary()
        if tok is not None and tok.kind == "op" and tok.value == "+":
            self.pos += 1
            return self._unary()
        return self._primary()

    def _primary(self) -> float:
        tok = self._next()
        if tok.kind == "num":
            assert isinstance(tok.value, float)
            return tok.value
        if tok.kind == "lparen":
            value = self._additive()
            close = self._peek()
            if close is None or close.kind != "rparen":
                raise CalculatorError("Missing closing parenthesis")
            self.pos += 1
            return value
        raise CalculatorError("Expected a number or parenthesis")


def evaluate(expression: str) -> float:
    """Evaluate an arithmetic expression. Raises CalculatorError on bad input."""
    if len(expression) > MAX_EXPRESSION_CHARS:
        raise CalculatorError(f"Expression too long (max {MAX_EXPRESSION_CHARS} chars)")
    result = _Parser(_tokenize(expression)).parse()
    if not math.isfinite(result):
        raise CalculatorError("Result is not a finite number")
    return result


def _format(value: float) -> str:
    return str(int(value)) if value.is_integer() and abs(value) < 1e15 else repr(value)


async def calculate_handler(args: dict[str, Any]) -> dict[str, Any]:
    """Handler behind the ``calculate`` tool; exported so tests can call it directly."""
    expression = str(args.get("expression", ""))
    try:
        value = evaluate(expression)
    except CalculatorError as exc:
        return {"content": [{"type": "text", "text": f"Cannot evaluate: {exc}"}], "is_error": True}
    return {"content": [{"type": "text", "text": f"{expression} = {_format(value)}"}]}


calculate_tool = tool(
    "calculate",
    "Evaluate an arithmetic expression exactly. Supports + - * / % ^ and parentheses. "
    "Use this instead of doing arithmetic in your head.",
    {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "minLength": 1,
                "maxLength": MAX_EXPRESSION_CHARS,
                "description": 'Expression, e.g. "(1200 * 1.081) / 12"',
            }
        },
        "required": ["expression"],
    },
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=False),
)(calculate_handler)
