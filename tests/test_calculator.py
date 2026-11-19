import pytest

from agent_kit_lite.tools.calculator import CalculatorError, calculate_handler, evaluate


@pytest.mark.parametrize(
    ("expr", "expected"),
    [
        ("1 + 2", 3),
        ("2 * 3 + 4", 10),
        ("2 * (3 + 4)", 14),
        ("10 / 4", 2.5),
        ("7 % 3", 1),
        ("2 ^ 10", 1024),
        ("2 ^ 3 ^ 2", 512),  # right-associative
        ("-3 + 5", 2),
        ("-(2 + 3) * 2", -10),
        ("1_000 * 1.081", 1081),
        ("(1200 * 1.081) / 12", 108.1),
        ("  3  ", 3),
    ],
)
def test_evaluate(expr: str, expected: float) -> None:
    assert evaluate(expr) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("expr", "fragment"),
    [
        ("", "Empty"),
        ("1 +", "end of expression"),
        ("(1 + 2", "closing parenthesis"),
        ("1 + 2)", "after end"),
        ("2 / 0", "Division by zero"),
        ("5 % 0", "Division by zero"),
        ("1.2.3", "Invalid number"),
        ("abc", "Unexpected character"),
        ("__import__('os')", "Unexpected character"),
        ("1; 2", "Unexpected character"),
    ],
)
def test_rejects(expr: str, fragment: str) -> None:
    with pytest.raises(CalculatorError, match=fragment):
        evaluate(expr)


def test_rejects_long_input() -> None:
    with pytest.raises(CalculatorError, match="too long"):
        evaluate("1+" * 300 + "1")


def test_rejects_non_finite() -> None:
    with pytest.raises(CalculatorError, match="finite"):
        evaluate("10 ^ 400")


async def test_handler_success_and_error() -> None:
    ok = await calculate_handler({"expression": "2 * 21"})
    assert ok["content"][0]["text"] == "2 * 21 = 42"
    assert "is_error" not in ok

    bad = await calculate_handler({"expression": "2 / 0"})
    assert bad["is_error"] is True
    assert "Division by zero" in bad["content"][0]["text"]
