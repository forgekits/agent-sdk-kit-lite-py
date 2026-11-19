# Changelog

## 0.1.0 (unreleased)

- Validated configuration from environment variables, standard library only.
- In-process MCP server with three tools: `calculate`, `save_note`, `search_notes`.
- `run_agent()` wrapper with locked-down SDK options, audit hook and run summary.
- CLI: `agent-kit "<prompt>"`.
- Unit tests with no API calls; opt-in integration test.
- CI on Linux and Windows, Python 3.10 and 3.13.
