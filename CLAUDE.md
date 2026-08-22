# HeatMind — Claude Code Instructions

## Project Rules

- Do what has been asked; nothing more, nothing less
- NEVER create files unless absolutely necessary — prefer editing existing files
- NEVER commit secrets, credentials, or .env files
- ALWAYS read a file before editing it
- Keep files under 500 lines
- Validate input at system boundaries

## Dead Code Policy

When dead code is found (functions, methods, or modules not called from production code):

1. **Do NOT delete it** — dead code often represents public API surface that tests exercise
2. **Wire it into the app** — add a call site in the UI, agent loop, CLI, or automation layer
3. **Write tests for it** — if no tests exist, create them in `tests/`
4. **Document it** — add a brief comment explaining why the function exists

If a function truly has no purpose and cannot be wired in, mark it with `# UNUSED` and leave it for future cleanup.

## Testing

- Run `pytest tests/ -x -q` before committing
- Run `ruff check .` and `ruff format --check .` for lint
- 898+ tests must pass, 0 failures

## Architecture

- `agents/` — ReAct agent loop, router, sub-agents
- `utils/` — 19 agentic patterns (verification, debate, trust, etc.)
- `api/` — FortyGuard API client
- `memory/` — Session memory, continuous learning
- `monitor/` — Autonomous monitoring loop
- `automation/` — Rule engine, scheduler
- `streamlit_app.py` — GUI (5 tabs: Chat, Dashboard, History, Monitor, Decision Audit)
- `main.py` — CLI (interactive mode + monitor)
