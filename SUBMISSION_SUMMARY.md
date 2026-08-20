# HeatMind — Submission Summary

**Track 06: Agentic AI** | **FortyGuard Hackathon'26**

---

## One Sentence

An autonomous multi-agent system that reasons about heat risk, acts without human approval, and tracks the USD cost of every decision — making the economics and accountability of AI autonomy fully transparent.

## The Problem

Extreme heat killed 61,000 people in Europe in summer 2022 (Lancet, 2023). The ILO estimates 2.4% of global working hours are lost annually to heat stress. Yet most cities still monitor heat reactively: a dashboard shows numbers, a human interprets them, and a decision arrives too late. The gap between detection and action costs lives.

## The Solution

HeatMind wraps the FortyGuard Temperature API in a multi-agent reasoning system. A coordinator agent plans which tools to call, executes them, reflects on the evidence, and — when conditions are dangerous — delegates to specialist sub-agents that draft and dispatch emergency alerts without human approval. Every decision carries a visible USD cost and a full audit trail.

## Five Agentic Patterns

1. **Self-Specifying Agents** — Each agent reads its own `agents/specs/*.md` operating manual at runtime. Roles are documents, not code.

2. **Reflective ReAct Loop** — Plan → Tool Calls → Observe → Reflect → Iterate (bounded to 2 rounds). The agent decides when it has enough evidence to conclude.

3. **Multi-Agent Handoffs** — Coordinator → Emergency Coordinator → Public Alert Agent. Each handoff is traced and auditable.

4. **Cost-Aware Autonomy** — Every LLM call and API call is logged to a cost ledger with estimated USD. The agent prefers cheaper sufficient tool paths ($0.013 for simple queries vs $0.067 for emergency drills).

5. **Decision Audit Trail** — Every step logged to MongoDB: reasoning, tool calls, reflections, delegations, cost, severity, outcome. Rendered as a live timeline in the Streamlit dashboard.

## What Judges Will See

| Criteria | HeatMind |
|---|---|
| **Autonomous action** | Multi-agent system plans, tools, reflects, delegates, alerts — without human approval |
| **Cost awareness** | Visible cost ledger; agent chooses cheaper paths when sufficient |
| **Decision accountability** | Full audit trail: reasoning, cost, severity, delegations |
| **Self-specification** | Agent roles defined in markdown, interpreted by LLM at runtime |
| **Production readiness** | 600+ tests, 90%+ coverage, Docker, CI/CD, multi-channel alerts |

## Demo

**Live:** [heatmind.streamlit.app](https://heatmind.streamlit.app)

1. Ask: "What's the heat index in Dubai right now?" → Watch the agent plan, call tools, reflect, answer. Open Monitor tab for cost breakdown.
2. Ask: "Run a simulated emergency drill for Phoenix" → Watch the full autonomous chain: coordinator → emergency coordinator → public alert → alerts dispatched.

Or run locally: `git clone` → `pip install` → `HEATMIND_DEMO_MODE=true python main.py`

## Tech

Python 3.14 · MongoDB 7 · FortyGuard API (all 6 endpoints) · OpenAI/Anthropic/Gemini/Ollama/Mock · Streamlit · Docker · MCP · 600+ tests · 90%+ coverage

---

*Built for FortyGuard Hackathon'26 — Because every degree matters.*
