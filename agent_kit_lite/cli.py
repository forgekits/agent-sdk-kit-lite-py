"""Command line entry point.

Usage:  agent-kit "your prompt"
The answer goes to stdout, logs and the run report go to stderr, so
``agent-kit "..." > answer.txt`` keeps them apart.
"""

from __future__ import annotations

import asyncio
import sys

from .agent import run_agent
from .config import ConfigError, load_config, require_api_key
from .logger import create_logger
from .report import explain_failure, format_summary


def _echo(text: str) -> None:
    sys.stdout.write(text)


async def _run(prompt: str) -> int:
    try:
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
    args = sys.argv[1:] if argv is None else argv
    prompt = " ".join(args).strip()
    if not prompt or prompt in ("-h", "--help"):
        sys.stderr.write('Usage: agent-kit "<prompt>"\n')
        return 0 if prompt else 2
    return asyncio.run(_run(prompt))


if __name__ == "__main__":
    raise SystemExit(main())
