"""Command line entry point.

Usage:  agent-kit "your prompt"        (console script, after pip install)
        python -m agent_kit_lite.cli "your prompt"
The answer goes to stdout, logs and the run report go to stderr, so
``agent-kit "..." > answer.txt`` keeps them apart. A .env file in the
current directory is loaded first. Exit codes: 0 ok, 1 run failed,
2 usage or config error.
"""

from __future__ import annotations

import asyncio
import sys

from .agent import run_agent
from .config import CONFIG_HELP, ConfigError, load_config, load_dotenv, require_api_key
from .logger import create_logger
from .report import explain_failure, format_summary

USAGE = f"""Usage: agent-kit "<prompt>"

Runs one prompt through the agent. Answer on stdout; JSON log lines and the
run report on stderr. Exit codes: 0 ok, 1 run failed, 2 usage or config error.

{CONFIG_HELP}

Only running a prompt needs the API key. ruff, mypy and pytest work without one."""


def _echo(text: str) -> None:
    sys.stdout.write(text)


async def _run(prompt: str) -> int:
    try:
        load_dotenv()
        config = load_config()
        require_api_key(config)
    except ConfigError as exc:
        sys.stderr.write(f"{exc}\n")
        return 2

    logger = create_logger(config.log_level)
    try:
        result = await run_agent(prompt, config, logger=logger, on_text=_echo)
    except Exception as exc:  # noqa: BLE001
        logger.error("run failed", error=str(exc))
        return 1
    sys.stdout.write("\n")
    sys.stderr.write("\n" + format_summary(result.summary) + "\n")
    why = explain_failure(result.summary)
    if why:
        sys.stderr.write(why + "\n")
    return 0 if result.summary.ok else 1


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(errors="replace")
    args = sys.argv[1:] if argv is None else argv
    prompt = " ".join(args).strip()
    if not prompt or prompt in ("-h", "--help"):
        sys.stderr.write(USAGE + "\n")
        return 0 if prompt else 2
    if args and args[0].startswith("-"):
        sys.stderr.write(f"Unknown option {args[0]!r}. Pass the prompt as the only argument.\n{USAGE}\n")
        return 2
    return asyncio.run(_run(prompt))


if __name__ == "__main__":
    raise SystemExit(main())
