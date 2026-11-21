# Agent SDK Kit (Lite) for Python

A small, tested starting point for building agents on the [Claude Agent SDK](https://code.claude.com/docs/en/agent-sdk/overview) in Python. It is what you would write in the first two days anyway: validated config, in-process tools, a locked-down `query()` wrapper, an audit hook, a cost report, a CLI and CI. MIT licensed. A [TypeScript edition](https://github.com/forgekits/agent-sdk-kit-lite) with the same layout exists.

It is not a framework. Under 1 000 lines of documented Python you can read in one sitting and delete what you do not need.

## What is in the box

| Piece | Module | What it gives you |
| --- | --- | --- |
| Config | `agent_kit_lite/config.py` | Environment variables validated with the standard library; fails fast with every problem listed; tiny `.env` loader |
| Tools | `agent_kit_lite/tools/` | `calculate` (safe parser, no `eval`), `save_note`, `search_notes` (file-backed store) |
| Agent | `agent_kit_lite/agent.py` | `run_agent()`: no built-in tools, no host settings, pre-approved tools only, turn and budget limits, audit hook |
| Report | `agent_kit_lite/report.py` | Flat `RunSummary` with cost, tokens, per-model usage and a one-line explanation of failures |
| CLI | `agent_kit_lite/cli.py` | `agent-kit "<prompt>"`, answer on stdout, report on stderr |
| Tests | `tests/` | Unit tests that never call the API; one opt-in integration test |
| CI | `.github/workflows/ci.yml` | Linux and Windows, Python 3.10 and 3.13 |

## Quick start

Requirements: Python 3.10 or later and an Anthropic API key from the Anthropic Console (not a `claude` login). The SDK package bundles the Claude Code binary; nothing else to install.

```bash
git clone https://github.com/forgekits/agent-sdk-kit-lite-py my-agent && cd my-agent
python -m venv .venv
source .venv/bin/activate            # macOS / Linux
# source .venv/Scripts/activate      # Windows, Git Bash
# .venv\Scripts\Activate.ps1         # Windows, PowerShell
pip install -e ".[dev]"
ruff check . && ruff format --check . && mypy && pytest -q    # no API key needed
```

Only running a prompt needs the key. Put it in a `.env` file in the directory you run from (the CLI reads it; blank lines mean "default"), or export it:

```bash
cp .env.example .env     # then edit: ANTHROPIC_API_KEY=sk-ant-...
# or, bash:        export ANTHROPIC_API_KEY=sk-ant-...
# or, PowerShell:  $env:ANTHROPIC_API_KEY = "sk-ant-..."
agent-kit "What is (1200 * 1.081) / 12? Then remember that my rent is 1200."
python -m agent_kit_lite.cli "..."   # same thing without the console script
```

You get the answer on stdout. On stderr come JSON log lines (one per tool call; set `LOG_LEVEL=warn` to silence them) and then a report like this:

```
status      ok (success)
turns       3
duration    6.2s total, 5.8s in API
cost        $0.0187 (local estimate)
tokens      in 2140, out 410, cache read 0, cache write 1800
model       claude-opus-5-5: $0.0187, in 2140, out 410
```

Exit codes: 0 ok, 1 run failed, 2 usage or configuration error. A run that hits a limit prints `status failed (error_max_turns)` plus one sentence on what to change. An invalid key prints `status failed (sdk error)` with the SDK's message under `errors`.

The default model is Opus-class. For cheap experiments set `AGENT_MODEL=claude-haiku-5-5` or `claude-sonnet-5-5`.

## Use it as a library

```python
import asyncio

from agent_kit_lite import load_config, load_dotenv, run_agent


async def main() -> None:
    load_dotenv()  # optional: read .env into os.environ
    config = load_config()  # reads and validates os.environ
    result = await run_agent(
        "Remember that the deploy window is Friday 16:00.",
        config,
        on_text=lambda t: print(t, end=""),
    )
    print(result.summary.ok, result.summary.text, result.summary.cost_usd, len(result.tool_calls))


asyncio.run(main())
```

`run_agent()` raises `ConfigError` when `ANTHROPIC_API_KEY` is missing. Without it the SDK would fall back to a Claude Code login on the host, which Anthropic does not permit for third-party products; pass `allow_host_credentials=True` only for local experiments.

`run_agent()` returns a `RunResult` with `summary`, `tool_calls` and `raw`:

| Field | Meaning |
| --- | --- |
| `summary.ok` | `True` when the run finished without error |
| `summary.subtype` | `"success"`, `"error_max_turns"`, `"error_max_budget_usd"`, `"error_during_execution"`, `"error_max_structured_output_retries"` |
| `summary.text` | the final answer (empty on failure) |
| `summary.cost_usd`, `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_write_tokens` | cost and tokens of the main loop; `cost_usd` is the SDK's local estimate |
| `summary.models` | per-model cost and tokens, including subagents |
| `summary.turns`, `duration_ms`, `api_ms`, `permission_denials`, `session_id`, `errors` | as reported by the SDK |
| `tool_calls` | `ToolCallRecord(tool, input, at)` for every tool call the audit hook saw |
| `raw` | the SDK's `ResultMessage`, if you need a field the summary does not expose |

### Add your own tools

Pass `@tool` functions in `extra_tools`; they are served next to the three built-in tools and covered by the same allow rule and audit hook:

```python
import json
from typing import Any

from claude_agent_sdk import ToolAnnotations, tool

from agent_kit_lite import load_config, run_agent

db = ...  # your database client


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


result = await run_agent("Look up order A1B2C3.", load_config(), extra_tools=[lookup_order])
```

To build a server with only your tools, use `create_sdk_mcp_server()` from the SDK and copy `build_options()` from `agent_kit_lite/agent.py`; keep the `mcp_servers` key `kit` so the allow pattern and the hook matcher still apply.

## Configuration

| Variable | Default | Bounds | Meaning |
| --- | --- | --- | --- |
| `ANTHROPIC_API_KEY` | required to run | | The SDK authenticates with an API key. Anthropic does not allow third-party products to use claude.ai subscription login. |
| `AGENT_MODEL` | `claude-opus-5-5` | | Model alias or full ID |
| `AGENT_MAX_TURNS` | `12` | 1 to 200 | Hard stop per run; result subtype becomes `error_max_turns` |
| `AGENT_MAX_BUDGET_USD` | `0.50` | more than 0, at most 100 | Hard stop per run; result subtype becomes `error_max_budget_usd` |
| `NOTES_DIR` | `./data/notes` | | Where `notes.jsonl` is written, relative to the current working directory; `data/` is git-ignored |
| `LOG_LEVEL` | `info` | `debug`, `info`, `warn`, `error` | JSON lines on stderr |

Blank values count as unset. `.env` is read by the CLI and by `load_dotenv()`; existing environment variables win over the file. On Windows, set `PYTHONUTF8=1` if non-ASCII characters in SDK messages show up garbled.

The notes store is one JSON object per line in `NOTES_DIR/notes.jsonl`, append-only, newest first on search. Bodies are capped at 20 000 characters and 10 tags.

## How the run is locked down

`build_options()` in `agent_kit_lite/agent.py` sets, and the unit tests assert:

- `tools=[]` removes every built-in tool. Claude can only call the MCP tools you register.
- `allowed_tools=["mcp__kit__*"]` pre-approves them; `permission_mode="dontAsk"` denies anything else instead of waiting for a human.
- `setting_sources=[]` ignores `~/.claude` and `.claude` on the host, so a developer's local hooks or CLAUDE.md never leak into production.
- `max_turns` and `max_budget_usd` end the run with a typed result you can branch on.
- A `PreToolUse` hook records every tool call. To block a call, return a deny decision from a hook of the same shape:

```python
async def no_long_expressions(input_data, tool_use_id, context):
    if (
        input_data.get("tool_name") == "mcp__kit__calculate"
        and len(input_data["tool_input"].get("expression", "")) > 100
    ):
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "expression too long",
            }
        }
    return {}


# register it next to the audit hook in build_options(): HookMatcher(matcher="^mcp__kit__", hooks=[audit, no_long_expressions])
```

## Testing

- `pytest -q` runs the unit tests. They cover the parser, the notes store, config validation, the `.env` loader, the report and the SDK options, and never call the API.
- The integration test runs one real query with a 0.30 USD cap and is skipped unless both variables are set:
  ```bash
  RUN_INTEGRATION=1 ANTHROPIC_API_KEY=sk-ant-... pytest tests/test_agent_integration.py          # bash
  $env:RUN_INTEGRATION="1"; $env:ANTHROPIC_API_KEY="sk-ant-..."; pytest tests/test_agent_integration.py   # PowerShell
  ```
- CI runs `ruff check`, `ruff format --check`, `mypy` and `pytest` on Linux and Windows with Python 3.10 and 3.13.

## Known limits

- Per-run limits only. Daily, per-customer or per-tenant budgets, persistent circuit breakers across restarts, and alerts are not part of the Lite kit.
- The notes store is a JSONL file: fine for a demo and single-process use, not for concurrent writers.
- `cost_usd` is the SDK's local estimate from list prices, not your invoice.
- The SDK moves fast. This kit requires `claude-agent-sdk>=0.2.185`; check its [changelog](https://github.com/anthropics/claude-agent-sdk-python/blob/main/CHANGELOG.md) when upgrading.

## Pro version

A paid Pro kit with per-day and per-customer cost caps, a persistent circuit breaker, tool permission policies with audit log, conversation storage, an eval harness for CI, metrics and deployment recipes is in preparation (TypeScript first). It will be linked here when it is available.

## License

MIT. See `LICENSE`. This project is independent and not affiliated with Anthropic; "Claude" is a trademark of Anthropic, PBC.
