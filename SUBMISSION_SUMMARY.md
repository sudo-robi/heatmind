# HeatMind — Submission Summary

**Track 06: Agentic AI** | **FortyGuard Hackathon'26**

---

## Problem

Extreme heat kills over 5 million people annually, and the crisis is accelerating. Current heat monitoring systems are reactive — they display raw temperature data and require humans to interpret it. There is no autonomous system that can reason about heat risk, remember past context, and trigger emergency responses without human intervention.

## Solution

HeatMind is a multi-agent heat intelligence system that wraps FortyGuard's Temperature API in autonomous agents capable of planning, calling, and deciding. Users ask natural language questions like "What's the heat risk for outdoor workers in Phoenix?" and the system routes the query to the optimal agent, executes multi-endpoint analysis, and delivers actionable intelligence with recommendations.

## Architecture

HeatMind implements five distinct agentic AI patterns in a single system:

1. **Session Memory** — MongoDB-backed persistence with UUID tracking, conversation history, and TTL expiration. The system remembers what you asked before and builds on it.

2. **Query Router** — Multi-factor classification (complexity × urgency) with confidence scoring. Simple queries go to the Quick Agent (single endpoint); complex queries trigger the Deep Agent (parallel multi-endpoint analysis); critical queries activate the Emergency Agent with immediate alert fan-out.

3. **Autonomous Monitor** — A scheduled polling loop that checks configured zones against heat thresholds 24/7. When conditions become dangerous, it triggers emergency responses without human intervention.

4. **Conversational Context** — Per-session conversation history enables multi-turn reasoning. Ask about Dubai, then "What about tomorrow?" — the system remembers the location and queries the forecast.

5. **Emergency Response** — Four-channel alert system (Console, Slack, Email, Webhook) fires simultaneously when thresholds are exceeded. No single point of failure.

## Technical Execution

- **5 specialized agents** across 3 complexity tiers
- **All 6 FortyGuard API endpoints** utilized (env_params, heatmap, heat_intel, satellite, streetview)
- **MCP integration** — exposes 5 tools so external AI agents (Claude, GPT, Gemini) can query HeatMind
- **460 tests** with 90%+ code coverage
- **Dual interface** — CLI for developers + Streamlit GUI with real-time dashboard
- **Docker-ready** with one-command deployment
- **Python 3.14**, ruff linting, GitHub Actions CI/CD

## Innovation

HeatMind is not just an API wrapper — it's an autonomous reasoning system. The NLP parser extracts location, time range, and data types from natural language. The Chain Agent chains multiple API calls to answer复合 questions. Public datasets (census tract health data, heat vulnerability indices) enrich raw temperature readings with socioeconomic context for risk scoring.

## Impact

- **Construction workers**: Real-time heat exposure monitoring with automatic evacuation alerts
- **Public events**: Stadium and festival heat tracking with threshold-based notifications
- **Urban planners**: Heat island identification with satellite and streetview ground truth
- **Emergency services**: Instant heat intelligence for first responders
- **Agriculture**: Crop and worker protection from heat damage

## Live Demo

**https://heatmind.streamlit.app**

Try asking: "What's the heat index in Dubai right now?" or "Start monitoring Phoenix for dangerous conditions."

---

*Built for FortyGuard Hackathon'26 — Because every degree matters.*
