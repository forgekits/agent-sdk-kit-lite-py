# Security

## What this kit does to keep an agent contained

- **No built-in tools.** `tools=[]` removes Bash, Read, Write, Edit, WebFetch and the rest. Claude can only call the tools you register.
- **No machine settings.** `setting_sources=[]` stops the SDK from loading `~/.claude` or `.claude` settings, hooks or CLAUDE.md files from the host.
- **No prompts that hang.** `permission_mode="dontAsk"` denies any tool that is not pre-approved instead of waiting for a human.
- **Hard limits per run.** `max_turns` and `max_budget_usd` end the run with a typed result instead of running away.
- **Safe arithmetic.** The calculator is a hand-written parser; it never evaluates code.
- **Bounded inputs.** Every tool schema has length and count limits.
- **Audit trail.** A `PreToolUse` hook records every tool call before it runs.

## What it does not do

- It does not stop a tool you add from doing harm. Give tools the narrowest access they need and check their arguments in the handler or in a `PreToolUse` hook.
- It does not protect secrets you put in prompts or notes. Treat the notes file as plain text.
- It does not rate-limit or authenticate callers of your application. That is your server's job.

## Reporting a vulnerability

Open a private security advisory at https://github.com/forgekits/agent-sdk-kit-lite-py/security/advisories (address to be confirmed before release). Please do not open a public issue for a vulnerability. You will get an acknowledgement within 72 hours.
