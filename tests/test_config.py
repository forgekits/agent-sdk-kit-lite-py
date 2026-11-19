import pytest

from agent_kit_lite.config import ConfigError, load_config, require_api_key


def test_defaults() -> None:
    c = load_config({})
    assert c.model == "claude-opus-5-5"
    assert c.max_turns == 12
    assert c.max_budget_usd == 0.5
    assert c.notes_dir == "./data/notes"
    assert c.log_level == "info"
    assert c.api_key is None


def test_reads_values() -> None:
    c = load_config(
        {
            "AGENT_MAX_TURNS": "3",
            "AGENT_MAX_BUDGET_USD": "2.5",
            "LOG_LEVEL": "debug",
            "ANTHROPIC_API_KEY": "k",
        }
    )
    assert c.max_turns == 3
    assert c.max_budget_usd == 2.5
    assert c.log_level == "debug"
    assert c.api_key == "k"


def test_lists_every_problem() -> None:
    with pytest.raises(ConfigError) as info:
        load_config({"AGENT_MAX_TURNS": "0", "AGENT_MAX_BUDGET_USD": "-1", "LOG_LEVEL": "loud"})
    msg = str(info.value)
    assert "AGENT_MAX_TURNS" in msg
    assert "AGENT_MAX_BUDGET_USD" in msg
    assert "LOG_LEVEL" in msg


def test_require_api_key() -> None:
    with pytest.raises(ConfigError, match="ANTHROPIC_API_KEY"):
        require_api_key(load_config({}))
    require_api_key(load_config({"ANTHROPIC_API_KEY": "k"}))
