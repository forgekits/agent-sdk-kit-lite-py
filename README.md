# Agent SDK Kit (Lite) for Python

A small, tested starting point for building agents on the [Claude Agent SDK](https://code.claude.com/docs/en/agent-sdk/overview) in Python. It is what you would write in the first two days anyway: validated config, in-process tools, a locked-down `query()` wrapper, an audit hook, a cost report, a CLI and CI. MIT licensed. A [TypeScript edition](../agent-sdk-kit-lite-ts) with the same layout exists.

It is not a framework. About 600 lines you can read in one sitting and delete what you do not need.

## What is in the box

| Piece | Module | What it gives you |
| --- | --- | --- |
| Config | `agent_kit_lite/config.py` | Environment variables validated with the standard library; fails fast with every problem listed |
| Tools | `agent_kit_lite/tools/` | `calculate` (safe parser, no `eval`), `save_note`, `search_notes` (file-backed store) |
| Agent | `agent_kit_lite/agent.py` | `run_agent()`: no built-in tools, no host settings, pre-approved tools only, turn and budget limits, audit hook |
| Report | `agent_kit_lite/report.py` | Flat `RunSummary` with cost, tokens, per-model usage and a one-line explanation of failures |
| CLI | `agent_kit_lite/cli.py` | `agent-kit "<prompt>"`, answer on stdout, report on stderr |
| Tests | `tests/` | Unit tests that never call the API; one opt-in integration test |
| CI | `.github/workflows/ci.yml` | Linux and Windows, Python 3.10 and 3.13 |

## Quick start

Requirements: Python 3.10 or later and an Anthropic API key. The SDK package bundles the Claude Code binary; nothing else to install.

```bash
git clone <this repo> my-agent && cd my-agent
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env                                 # put your ANTHROPIC_API_KEY in .env, then export it
agent-kit "What is (1200 * 1.081) / 12? Then remember that my rent is 1200."
```

You get the answer on stdout and a report like this on stderr:

```
status      ok (success)
turns       3
duration    6.2s total, 5.8s in API
cost        $0.0187 (local estimate)
tokens      in 2140, out 410, cache read 0, cache write 1800
model       claude-opus-5-5: $0.0187, in 2140, out 410
```

Run the checks (no API key needed):

```bash
ruff check . && mypy && pytest -q
```

## Use it as a library

```python
import asyncio
import sys

from agent_kit_lite import load_config, run_agent


async def main() -> None:
    config = load_config()  # reads os.environ
    result = await run_agent(
        "Remember that the deploy window is Friday 16:00.",
        config,
        on_text=lambda t: sys.stdout.write(t),
    )
    print(result.summary.ok, result.summary.cost_usd, len(result.tool_calls))


asyncio.run(main())
```

Add your own tools next to the built-in ones:

```python
from typing import Any

from claude_agent_sdk import ToolAnnotations, create_sdk_mcp_server, tool

from agent_kit_lite import calculate_tool


@tool(
    "lookup_order",
    "Fetch an order by id from our system",
    {
        "type": "object",
        "properties": {"id": {"type": "string", "pattern": "^[A-Z0-9-]{6,20}$"}},
        "required": ["id"],
    },
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def lookup_order(args: dict[str, Any]) -> dict[str, Any]:
    order = await db.orders.get(args["id"])
    return {"content": [{"type": "text", "text": json.dumps(order)}]}


server = create_sdk_mcp_server(name="shop", version="1.0.0", tools=[calculate_tool, lookup_order])
```

Then pass `server` where `create_kit_server()` is used, or copy `build_options()` and change the `mcp_servers` key.

## Configuration

| Variable | Default | Meaning |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | required for the CLI | The SDK authenticates with an API key. Anthropic does not allow third-party products to use claude.ai subscription login. |
| `AGENT_MODEL` | `claude-opus-5-5` | Model alias or full ID |
| `AGENT_MAX_TURNS` | `12` | Hard stop per run; result subtype becomes `error_max_turns` |
| `AGENT_MAX_BUDGET_USD` | `0.50` | Hard stop per run; result subtype becomes `error_max_budget_usd` |
| `NOTES_DIR` | `./data/notes` | Where `notes.jsonl` lives |
| `LOG_LEVEL` | `info` | `debug`, `info`, `warn`, `error`; JSON lines on stderr |

## How the run is locked down

`build_options()` in `agent_kit_lite/agent.py` sets, and the unit tests assert:

- `tools=[]` removes every built-in tool. Claude can only call the MCP tools you register.
- `allowed_tools=["mcp__kit__*"]` pre-approves them; `permission_mode="dontAsk"` denies anything else instead of waiting for a human.
- `setting_sources=[]` ignores `~/.claude` and `.claude` on the host, so a developer's local hooks or CLAUDE.md never leak into production.
- `max_turns` and `max_budget_usd` end the run with a typed result you can branch on.
- A `PreToolUse` hook records every tool call. To block or rewrite calls, return `hookSpecificOutput` with `permissionDecision: "deny"` or `updatedInput` from the same hook; see `create_audit_hook()`.

## Testing

- `pytest -q` runs the unit tests. They cover the parser, the notes store, config validation, the report and the SDK options, and never call the API.
- `RUN_INTEGRATION=1 ANTHROPIC_API_KEY=... pytest tests/test_agent_integration.py` runs one real query with a 0.30 USD cap.

## Known limits

- Per-run limits only. Daily, per-customer or per-tenant budgets, persistent circuit breakers across restarts, and alerts are not part of the Lite kit.
- The notes store is a JSONL file: fine for a demo and single-process use, not for concurrent writers.
- `cost_usd` is the SDK's local estimate from list prices, not your invoice.
- The SDK moves fast. This kit requires `claude-agent-sdk>=0.2.185`; check its [changelog](https://github.com/anthropics/claude-agent-sdk-python/blob/main/CHANGELOG.md) when upgrading.

## Pro version

A paid Pro kit with per-day and per-customer cost caps, a persistent circuit breaker, tool permission policies with audit log, session storage, an eval harness for CI, OpenTelemetry export and deployment recipes is in preparation. It will be linked here when it is available.

## License

MIT. See `LICENSE`. This project is independent and not affiliated with Anthropic; "Claude" is a trademark of Anthropic, PBC.
