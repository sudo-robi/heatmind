# HeatMind — Submission Summary

**Track 06: Agentic AI** | **FortyGuard Hackathon'26**

---

## Problem

Extreme heat kills over 5 million people annually, and the crisis is accelerating. Current heat monitoring systems are reactive — they display raw temperature data and require humans to interpret it. There is no autonomous system that can reason about heat risk, remember past context, and trigger emergency responses without human intervention.

## Solution

HeatMind is an **autonomous multi-agent system** that wraps FortyGuard's Temperature API in an agentic reasoning core. Users ask natural language questions like "What's the heat risk for outdoor workers in Phoenix?" and HeatMind plans a tool strategy, executes it, **reflects on the evidence**, iterates if needed, and delegates to specialist sub-agents that act — including dispatching public alerts — **without human approval**.

## What Makes It Autonomous (Track 06)

### 1. Reflective ReAct Loop

HeatMind's LLM core is not a single prompt — it is a loop:

```
Plan → Tool Calls → Observe → REFLECT → enough evidence? → Synthesize
  ▲                             │
  └────── gather more ──────────┘   → SUFFICIENT → answer
```

After each round of tool execution the LLM inspects the observations and decides whether to gather more evidence (bounded to 2 rounds) or conclude. If a tool fails, the agent degrades gracefully to demo data rather than stranding the loop. Works against OpenAI, Anthropic, Gemini, local Ollama, or a deterministic Mock (zero-config demos and CI).

### 2. Self-Specifying Agents

Every agent is defined by a markdown spec (`agents/specs/*.md`) with YAML frontmatter — name, description, tools, autonomy level — plus its decision rules. At runtime **the agent loads its own spec and the LLM reads it as its operating manual**, so roles, tool scopes, and escalation policy are documents, not code.

| Spec | Role |
|---|---|
| `coordinator` | Lead agent — plans tool strategy, reflects, delegates |
| `heat-analyst` | Deep thermal/environmental correlation on observations |
| `emergency-coordinator` | Severity assessment + escalation decision (advisory/alert/evacuation) |
| `public-alert` | Drafts + dispatches public alerts to all channels |

### 3. Sub-Agent Handoffs

When the reflective loop assesses dangerous conditions, the coordinator **hands off** to the Emergency Coordinator (DECIDE phase), which authorizes notification, then to the Public Alert agent (ALERT phase), which drafts and dispatches the alert. Each handoff appears in the reasoning trace as agent-to-agent communication — fully auditable.

### 4. Cost-Aware Autonomy

Track 06 judges prize *pragmatic, cost-aware AI*. Every LLM call and API call is recorded in a **cost ledger** with estimated USD; the agent is prompted to prefer the cheapest sufficient tool path (`env_params` over `heatmap` + `heat_intelligence` for simple lookups). The economics of autonomy are visible in the UI.

### 5. Decision Audit Trail

Every autonomous decision — plan, tool call, reflection, sub-agent handoff, alert — is logged to MongoDB with its reasoning, LLM mode, severity, and cost, and rendered as a live **Autonomous Decision Audit** timeline in the Monitor tab.

## Supporting Systems

- **Session Memory** — MongoDB-backed persistence with UUID tracking, conversation history, and TTL expiration. The system remembers what you asked before and builds on it.
- **Query Router** — Multi-factor classification (complexity × urgency) with confidence scoring. Simple queries use lightweight endpoints; complex queries trigger comprehensive analysis; critical queries activate emergency response.
- **Autonomous Monitor** — A scheduled polling loop that checks configured zones against heat thresholds 24/7 (with simulation mode for demos).
- **Emergency Response** — Four-channel alert system (Console, Slack, Email, Webhook) fires simultaneously when the coordinator authorizes it. No single point of failure.
- **Live Thermal Maps** — Interactive pydeck heat-risk maps rendered from real FortyGuard heatmap GeoJSON.

## Technical Execution

- **4 spec-defined agents** + 3 legacy deterministic agents across 3 complexity tiers
- **All 5 FortyGuard API endpoints** utilized (env_params, heatmap, heat_intel, satellite, streetview)
- **Reflective ReAct loop** with bounded evidence-gathering iterations
- **Cost ledger** with per-decision USD estimates
- **MCP integration** — exposes 5 tools so external AI agents (Claude, GPT, Gemini) can query HeatMind
- **598 tests** with 90%+ code coverage
- **Dual interface** — CLI for developers + Streamlit GUI with real-time dashboard and decision audit
- **Docker-ready** with one-command deployment
- **Python 3.14**, ruff linting, GitHub Actions CI/CD

## Impact

- **Construction workers**: Real-time heat exposure monitoring with automatic evacuation alerts
- **Public events**: Stadium and festival heat tracking with threshold-based notifications
- **Urban planners**: Heat island identification with satellite and streetview ground truth
- **Emergency services**: Instant heat intelligence for first responders
- **Agriculture**: Crop and worker protection from heat damage

## Live Demo

**https://heatmind.streamlit.app**

Try asking: "What's the heat index in Dubai right now?" or "Run a simulated emergency drill" — then open the Monitor tab to watch the autonomous decision audit populate.

---

*Built for FortyGuard Hackathon'26 — Because every degree matters.*