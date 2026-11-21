from pathlib import Path

import pytest

from agent_kit_lite.config import ConfigError, load_config, load_dotenv, require_api_key


def test_blank_values_mean_defaults() -> None:
    c = load_config(
        {
            "ANTHROPIC_API_KEY": "",
            "AGENT_MODEL": " ",
            "AGENT_MAX_TURNS": "",
            "AGENT_MAX_BUDGET_USD": "",
            "LOG_LEVEL": "",
        }
    )
    assert c.api_key is None
    assert c.model == "claude-opus-5-5"
    assert c.max_turns == 12
    assert c.log_level == "info"
    with pytest.raises(ConfigError, match="ANTHROPIC_API_KEY"):
        require_api_key(c)


def test_load_dotenv_missing_file(tmp_path: Path) -> None:
    target: dict[str, str] = {}
    assert load_dotenv(tmp_path / "nope.env", target) == []
    assert target == {}


def test_load_dotenv_parses_and_does_not_overwrite(tmp_path: Path) -> None:
    file = tmp_path / ".env"
    file.write_text(
        "\r\n".join(
            [
                "# comment",
                "",
                "ANTHROPIC_API_KEY=sk-ant-test",
                'AGENT_MODEL="claude-haiku-5-5"',
                "export LOG_LEVEL='debug'",
                "AGENT_MAX_TURNS=7 # inline comment",
                "NOTES_DIR=",
                "not a valid line",
                "AGENT_MAX_BUDGET_USD = 0.25",
            ]
        ),
        encoding="utf-8",
    )
    target = {"AGENT_MODEL": "already-set"}
    assert load_dotenv(file, target) == [
        "ANTHROPIC_API_KEY",
        "LOG_LEVEL",
        "AGENT_MAX_TURNS",
        "NOTES_DIR",
        "AGENT_MAX_BUDGET_USD",
    ]
    assert target == {
        "AGENT_MODEL": "already-set",
        "ANTHROPIC_API_KEY": "sk-ant-test",
        "LOG_LEVEL": "debug",
        "AGENT_MAX_TURNS": "7",
        "NOTES_DIR": "",
        "AGENT_MAX_BUDGET_USD": "0.25",
    }
    c = load_config(target)
    assert c.api_key == "sk-ant-test"
    assert c.max_turns == 7
    assert c.notes_dir == "./data/notes"
