<div align="center">

```
  ╔══════════════════════════════════════════════════════════════════╗
  ║                                                                ║
  ║     🔥🔥🔥    H E A T M I N D    🔥🔥🔥                       ║
  ║                                                                ║
  ║     Track 06: Agentic AI — FortyGuard Hackathon'26             ║
  ║                                                                ║
  ║     An autonomous multi-agent system that reasons about        ║
  ║     heat risk, acts without human approval, and tracks         ║
  ║     the cost of every decision.                                ║
  ║                                                                ║
  ╚══════════════════════════════════════════════════════════════════╝
```

[![Python 3.14](https://img.shields.io/badge/Python-3.14-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![MongoDB](https://img.shields.io/badge/MongoDB-7-47A248?style=for-the-badge&logo=mongodb&logoColor=white)](https://mongodb.com)
[![FortyGuard](https://img.shields.io/badge/FortyGuard-API-E63946?style=for-the-badge)](https://fortyguard.io)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.0-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
[![MCP](https://img.shields.io/badge/MCP-Compatible-8B5CF6?style=for-the-badge)](https://modelcontextprotocol.io)
[![Tests](https://img.shields.io/badge/Tests-600+-00C853?style=for-the-badge)](https://pytest.org)
[![Coverage](https://img.shields.io/badge/Coverage-90%25-FFD600?style=for-the-badge)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-00BFA5?style=for-the-badge)](LICENSE)

**[Live Demo →](https://heatmind.streamlit.app)** | [GitHub Repo →](https://github.com/sudo-robi/heatmind)

---

</div>

## The Problem: Heat Kills in the Dark

**Extreme heat is the deadliest weather-related killer in Europe, claiming over 61,000 lives in the summer of 2022 alone** (Lancet, 2023). The ILO estimates **2.4% of global working hours are lost annually** to heat stress — the equivalent of 80 million full-time jobs. By 2030, heat-related productivity loss will cost the global economy **$2.4 trillion per year**.

Yet most cities still monitor heat reactively: a dashboard shows raw temperature data, a human checks it, and a decision is made — often too late. Construction workers collapse before a warning is issued. Outdoor event attendees are already dehydrated by the time a report is filed. **The gap between detection and action costs lives.**

Current solutions fail for three reasons:

| Failure Mode | What Happens |
|---|---|
| **No reasoning** | Dashboards show numbers. No agent interprets what 48°C heat index means for outdoor workers in this specific zone. |
| **No autonomy** | A human must notice the alert, decide severity, and manually trigger warnings. In a crisis, this is the bottleneck. |
| **No accountability** | When an alert is issued (or missed), there is no audit trail. Which data was considered? What reasoning led to the decision? Why was the threshold not triggered? |

**HeatMind solves all three.** It is an autonomous agent that reasons about heat risk, acts without human approval, and logs every decision with its cost.

---

## What HeatMind Does

HeatMind wraps the FortyGuard Temperature API in a **multi-agent reasoning system**. A coordinator agent reads a natural language query, plans which API tools to call, executes them, reflects on the evidence, and — if conditions are dangerous — delegates to specialist sub-agents that draft and dispatch emergency alerts **without waiting for human approval**.

The system is self-specifying: each agent reads its own markdown operating manual at runtime, so roles and escalation policies are documents, not code. Every LLM call and API call is tracked in a **cost ledger** with estimated USD, and every autonomous decision is logged to a **decision audit trail** — making the economics and reasoning of autonomy fully transparent.

---

## How It Works: Five Agentic Patterns

HeatMind implements **five distinct agentic AI patterns** that compose into a single autonomous system:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        HEATMIND AGENTIC STACK                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ PATTERN 1: SELF-SPECIFYING AGENTS                               │   │
│  │                                                                  │   │
│  │  agents/specs/coordinator.md  ──▶ LLM reads at runtime          │   │
│  │  agents/specs/heat-analyst.md ──▶ defines role + tools + rules  │   │
│  │  agents/specs/emergency-coordinator.md                          │   │
│  │  agents/specs/public-alert.md                                   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ PATTERN 2: REFLECTIVE ReAct LOOP                                │   │
│  │                                                                  │   │
│  │  Plan ──▶ Tool Calls ──▶ Observe ──▶ REFLECT ──▶ Synthesize    │   │
│  │    ▲                        │              │                     │   │
│  │    └── gather more ◀────────┘              └──▶ enough evidence │   │
│  │         (bounded to 2 rounds)                                    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ PATTERN 3: MULTI-AGENT HANDOFFS                                 │   │
│  │                                                                  │   │
│  │  Coordinator ──▶ Emergency Coordinator ──▶ Public Alert Agent   │   │
│  │    (PLAN)            (DECIDE)                  (ALERT)           │   │
│  │    "What's the       "Severity is EXTREME,   "Drafting alert    │   │
│  │     heat risk?"      authorize alerts"       to all channels"   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ PATTERN 4: COST-AWARE AUTONOMY                                  │   │
│  │                                                                  │   │
│  │  Cost Ledger:                                                   │   │
│  │    env_params: $0.01  ◀── agent prefers this for simple queries │   │
│  │    heatmap: $0.02                                              │   │
│  │    heat_intelligence: $0.03                                     │   │
│  │    LLM calls: tracked per phase (plan / reflect / synthesize)   │   │
│  │    TOTAL per decision: visible in UI + audit log                │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ PATTERN 5: DECISION AUDIT TRAIL                                 │   │
│  │                                                                  │   │
│  │  Every step logged to MongoDB:                                   │   │
│  │    reasoning │ tool calls │ reflections │ delegations │ cost     │   │
│  │    severity  │ LLM mode   │ outcome     │ timestamp  │ alert    │   │
│  │                                                                  │   │
│  │  Rendered as live timeline in Streamlit Monitor tab              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Cost-Aware Autonomy: The Economics of Every Decision

**This is what separates HeatMind from a chatbot wrapper.** Every autonomous decision carries a visible USD cost. The agent is *prompted to prefer cheaper sufficient tool paths* — it does not call the expensive `heat_intelligence` endpoint when `env_params` answers the question.

### Cost Ledger Example

A typical query — "What's the heat index in Dubai right now?" — costs:

| Step | Operation | Cost (USD) |
|---|---|---|
| 1 | LLM plan phase | ~$0.0008 |
| 2 | FortyGuard `env_params` call | $0.01 |
| 3 | LLM reflect phase | ~$0.0005 |
| 4 | LLM synthesize phase | ~$0.0012 |
| **Total** | | **~$0.013** |

A complex emergency drill — "Run a full heat risk assessment for Phoenix and alert if dangerous" — costs:

| Step | Operation | Cost (USD) |
|---|---|---|
| 1 | LLM plan phase | ~$0.0008 |
| 2 | `env_params` | $0.01 |
| 3 | `heatmap` | $0.02 |
| 4 | `heat_intelligence` | $0.03 |
| 5 | LLM reflect phase (×2) | ~$0.001 |
| 6 | Emergency Coordinator sub-agent | ~$0.002 |
| 7 | Public Alert sub-agent | ~$0.002 |
| 8 | LLM synthesize phase | ~$0.0015 |
| **Total** | | **~$0.067** |

**The agent chooses the $0.013 path for simple queries and the $0.067 path when the situation demands it.** This is cost-aware autonomy — not cost-blind automation.

The Streamlit dashboard surfaces the full cost ledger so you can see exactly what every decision cost and why.

---

## Demo

**Try it live: [heatmind.streamlit.app](https://heatmind.streamlit.app)**

### Quick Test (30 seconds)

1. Open the app
2. Type: `What's the heat index in Dubai right now?`
3. Watch the agent plan, call tools, reflect, and answer
4. Click the **Monitor** tab to see the decision audit trail with cost breakdown

### Emergency Scenario (2 minutes)

1. Type: `Run a simulated emergency drill for Phoenix`
2. Watch the coordinator plan → call multiple tools → reflect → delegate to Emergency Coordinator → delegate to Public Alert agent → dispatch alerts
3. Open the **Monitor** tab to see the full autonomous chain: each sub-agent handoff, each reflection, each cost entry

### CLI Demo

```bash
git clone https://github.com/sudo-robi/heatmind.git && cd heatmind
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # or set HEATMIND_DEMO_MODE=true
python main.py
```

Set `HEATMIND_DEMO_MODE=true` in `.env` to run the full autonomous agent loop with synthetic data — no API or LLM key required.

---

## Architecture

### System Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          HEATMIND SYSTEM                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌─────────────┐    ┌──────────────┐    ┌─────────────────────────┐  │
│   │  CLI / GUI  │───▶│ Query Router │───▶│   LLMAgent (Agentic)    │  │
│   │  (User)     │    │              │    │                         │  │
│   └─────────────┘    │ • Complexity │    │  Plan → Tools → Observe  │  │
│                      │ • Urgency    │    │  → Reflect → Synthesize  │  │
│                      │ • Confidence │    │                         │  │
│                      └──────────────┘    │  ┌──────────┐           │  │
│                                          │  │   LLM    │ ─────────┼──│──▶ OpenAI / Anthropic /
│                                          │  │ Provider │  fallback│  │    Gemini / Ollama / Mock
│                                          │  └──────────┘           │  │
│                                          │  ┌──────────┐           │  │
│                                          │  │  Chain   │ ◀─ LLM   │  │
│                                          │  │  Agent   │  down    │  │
│                                          │  └──────────┘           │  │
│                                          │  ┌──────────────┐       │  │
│                                          │  │  Emergency   │       │  │
│                                          │  │  Agent       │ ◀─── │  │
│                                          │  └──────────────┘       │  │
│                                          │    Critical alerts      │  │
│                                          └─────────────────────────┘  │
│                                                     │                  │
│                                                     ▼                  │
│                                          ┌─────────────────────┐      │
│                                          │   Session Memory    │      │
│                                          │   (MongoDB)         │      │
│                                          └─────────────────────┘      │
│                                                     │                  │
│   ┌──────────────────────────────────────────────┐  │                  │
│   │          FortyGuard Temperature API           │  │                  │
│   │  env_params │ heatmap │ heat_intel │ satellite │ streetview       │  │
│   └──────────────────────────────────────────────┘  │                  │
│                                                     ▼                  │
│                                          ┌─────────────────────┐      │
│                                          │   Autonomous Loop   │      │
│                                          │   CronJob → Check   │      │
│                                          │   → Threshold →     │      │
│                                          │   Emergency Agent   │      │
│                                          └─────────────────────┘      │
│                                                     │                  │
│                                                     ▼                  │
│   ┌───────────────────────────────────────────────────────────────┐   │
│   │   Alert System: Console │ Slack │ Webhook │ Email │ MCP       │   │
│   └───────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Self-Specifying Agents

Each agent reads its own markdown spec at runtime. The spec defines the agent's role, available tools, decision rules, and autonomy policy — in plain English that the LLM interprets:

| Spec File | Agent Role | Autonomy Level |
|---|---|---|
| `agents/specs/coordinator.md` | Lead — plans tool strategy, reflects, delegates | Full |
| `agents/specs/heat-analyst.md` | Specialist — deep thermal/environmental correlation | Scoped |
| `agents/specs/emergency-coordinator.md` | DECIDE phase — severity assessment, escalation | Scoped |
| `agents/specs/public-alert.md` | ALERT phase — drafts + dispatches alerts | Scoped |

**Why this matters:** Roles and escalation policies are documents, not hardcoded if-else trees. Changing the threshold from 38°C to 40°C is a markdown edit, not a code deploy.

### Reflective ReAct Loop

The LLM core is not a single prompt — it is a bounded loop:

```
Plan ──▶ Tool Calls ──▶ Observe ──▶ REFLECT ──▶ enough evidence?
  ▲                        │              │
  └────── gather more ◀────┘              └──▶ SUFFICIENT → answer
       (max 2 rounds)
```

After each tool execution round, the LLM inspects observations and decides: gather more evidence or conclude? If a tool fails, the agent degrades gracefully to demo data rather than crashing.

### Sub-Agent Handoff Chain

When the coordinator assesses dangerous conditions (heat index ≥ 38°C):

```
Coordinator (PLAN)
    │  "Heat index 47°C in zone — delegating"
    ▼
Emergency Coordinator (DECIDE)
    │  "Severity: EXTREME. Authorize autonomous alerts."
    ▼
Public Alert Agent (ALERT)
    │  "Drafting alert to Console + Slack + Webhook + Email"
    ▼
Alert System fires all channels simultaneously
```

Each handoff appears in the reasoning trace as agent-to-agent communication — fully auditable.

### Decision Audit Trail

Every autonomous decision is logged to MongoDB with:

| Field | Purpose |
|---|---|
| `reasoning` | What the agent decided and why |
| `tool_calls` | Which API endpoints were called |
| `llm_mode` | Which LLM provider was used |
| `severity` | Assessed risk level |
| `cost_usd` | Total cost of this decision |
| `delegations` | Which sub-agents were invoked |
| `outcome` | completed / error / fallback |
| `timestamp` | When the decision was made |

---

## Track 06 Alignment: Agentic AI Criteria

| Criterion | How HeatMind Scores |
|---|---|
| **Autonomous action** | Multi-agent system acts without human approval: plans, tools, reflects, delegates, alerts. Not a single LLM call. |
| **Self-specifying agents** | Each agent reads its own `agents/specs/*.md` operating manual at runtime — roles are documents, not code. |
| **Reflective reasoning** | Bounded ReAct loop (plan → tool → observe → reflect → iterate) with evidence sufficiency checks. |
| **Cost-aware autonomy** | Every decision carries a USD cost in the ledger; agent prefers cheaper sufficient tool paths. |
| **Decision audit trail** | Every step logged with reasoning, cost, severity, delegations — rendered as live timeline. |
| **Multi-agent coordination** | Coordinator → Emergency Coordinator → Public Alert handoff chain with traced communication. |
| **Graceful degradation** | Falls back to ChainAgent (deterministic) when LLM is unavailable; falls back to demo data when API is unavailable. |
| **Production-ready** | 600+ tests, 90%+ coverage, Docker, CI/CD, MongoDB, multi-channel alerts. |
| **MCP integration** | Exposes 5 tools via Model Context Protocol — composable with any AI agent ecosystem. |

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Language** | Python 3.14 |
| **LLM Core** | OpenAI / Anthropic / Gemini / Ollama / Mock (deterministic fallback) |
| **Agent Specs** | Markdown + YAML frontmatter (`agents/specs/*.md`) |
| **Database** | MongoDB 7 (session memory, decision audit trail) |
| **API** | FortyGuard Temperature API (all 6 endpoints) |
| **Maps** | pydeck (interactive thermal risk visualization) |
| **CLI** | Rich (terminal UI) |
| **GUI** | Streamlit (web dashboard + decision audit timeline) |
| **Alerts** | Console / Slack / SMTP / Webhooks |
| **Integration** | MCP (Model Context Protocol) |
| **Testing** | pytest + coverage (600+ tests, 90%+) |
| **CI/CD** | GitHub Actions |
| **Deployment** | Docker + Docker Compose |

---

## Quick Start

```bash
# Clone and setup
git clone https://github.com/sudo-robi/heatmind.git
cd heatmind
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# Start MongoDB
docker run -d --name heatmind-mongo -p 27017:27017 mongo:7

# Run CLI
python main.py

# OR run GUI
streamlit run streamlit_app.py

# OR run demo mode (no API/LLM keys needed)
# Set HEATMIND_DEMO_MODE=true in .env, then:
python main.py
```

---

## Environment Variables

```env
# Required
FORTYGUARD_API_KEY=your_api_key_here

# MongoDB
MONGO_URI=mongodb://localhost:27017
MONGO_DB=heatmind

# LLM Provider (optional — demo mode works without any)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Slack Alerts (optional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Email Alerts (optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_app_password
ALERT_EMAIL_TO=recipient@example.com

# Webhook Alerts (optional)
ALERT_WEBHOOK_URL=https://your-webhook-url.com/alerts

# Monitor Settings
MONITOR_INTERVAL_MINUTES=30
HEAT_THRESHOLD_C=40
HEAT_INDEX_THRESHOLD=45

# Demo Mode — run full autonomous loop with synthetic data
HEATMIND_DEMO_MODE=false
```

---

## Industry Use Cases

| Sector | Application |
|---|---|
| **Construction** | Monitor outdoor worker heat exposure; auto-trigger evacuation alerts |
| **Public Events** | Track heat at stadiums/festivals; threshold-based notifications |
| **Agriculture** | Protect crops and workers from heat damage |
| **Urban Planning** | Identify heat islands with satellite + streetview ground truth |
| **Emergency Services** | Instant heat intelligence for first responders |
| **Facility Management** | Monitor HVAC load and outdoor conditions |

---

## Testing

```bash
pytest tests/ -v                                  # all tests
pytest tests/ --cov=. --cov-report=term-missing   # with coverage
pytest tests/test_llm_agent.py -v                  # agent logic
pytest tests/test_cost_ledger.py -v                # cost tracking
pytest tests/test_integration.py -v               # end-to-end flows
```

| Module | Coverage |
|---|---|
| `agents/quick_agent.py` | 100% |
| `agents/deep_agent.py` | 100% |
| `agents/emergency_agent.py` | 100% |
| `agents/router.py` | 97% |
| `memory/session.py` | 100% |
| `utils/alerts.py` | 100% |
| `config.py` | 100% |
| `api/fortyguard.py` | 91% |

---

<div align="center">

**Built for FortyGuard Hackathon'26 — Track 06: Agentic AI**

```
🔥 HeatMind — Because every degree matters. 🔥
```

</div>
