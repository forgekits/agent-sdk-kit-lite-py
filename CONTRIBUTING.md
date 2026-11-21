# Contributing

Thanks for taking a look. Small, focused pull requests are easiest to review.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate            # Windows Git Bash: source .venv/Scripts/activate; PowerShell: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
ruff check . && ruff format --check . && mypy && pytest -q    # no API key needed, same as CI
```

## Before you open a PR

- Add or update a test in `tests/` for anything you change in `agent_kit_lite/`.
- Keep unit tests free of API calls. Anything that hits the API goes into `tests/test_agent_integration.py` behind `RUN_INTEGRATION=1`.
- Run the four checks locally (ruff check, ruff format --check, mypy, pytest). CI runs them on Linux and Windows with Python 3.10 and 3.13.
- Describe the change and why in the PR body. One topic per PR.

## Reporting bugs

Open an issue with: the SDK version (`pip show claude-agent-sdk`), your Python version, the command you ran, and what you saw. Strip API keys and personal data from logs first.
