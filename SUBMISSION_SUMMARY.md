# HeatMind — Submission Summary

**Track 06: Agentic AI** | **FortyGuard Hackathon'26**

---

## One Sentence

An autonomous multi-agent system that reasons about heat risk, learns from every analysis, degrades gracefully under cost pressure, and makes the economics and accountability of AI autonomy fully transparent.

## The Problem

Extreme heat killed 61,000 people in Europe in summer 2022 (Lancet, 2023). The ILO estimates 2.4% of global working hours are lost annually to heat stress. Yet most cities still monitor heat reactively: a dashboard shows numbers, a human interprets them, and a decision arrives too late. The gap between detection and action costs lives.

## The Solution

HeatMind wraps the FortyGuard Temperature API in a multi-agent reasoning system. A coordinator agent plans which tools to call, executes them, reflects on the evidence, and — when conditions are dangerous — delegates to specialist sub-agents that draft and dispatch emergency alerts. Every decision carries a visible USD cost, a confidence score, and a full audit trace. The system learns from past analyses, routes to cheaper models when budgets are tight, self-heals when providers fail, and asks for human approval on high-stakes actions until it earns enough trust to act alone.

## Six Agentic Patterns

### 1. Continuous Learning
Every analysis extracts a pattern (zone, query_type, tools_used, severity, outcome). Past successful patterns are injected into the planning phase as guidance. The agent improves over time without retraining.

### 2. Cost-Aware Model Routing
Budget-gated tier selection: plan phase uses "fast" (cheap), reflect uses "balanced", synthesize uses "deep" (high quality). When budget drops below 20%, falls back to free MockLLM. Dashboard shows live budget gauge.

### 3. Circuit Breaker + Self-Healing
Per-provider circuit breaker: CLOSED (healthy) → OPEN (3 failures, 60s cooldown) → HALF-OPEN (test request) → CLOSED (recovered). Doubles cooldown on repeated failures. Monitor tab shows provider health status.

### 4. Event-Driven Automation
Rule engine evaluates conditions on every monitor check: heat_index ≥ 45 → trigger_emergency, rising trend + ≥ 40 → send_warning, anomaly detected → deep_analysis. Rules can be toggled on/off in the Monitor tab.

### 5. Structured Evidence Trail
Every decision gets a trace_id, per-phase spans (plan/execute/reflect/synthesize), cost attribution, confidence score, and outcome. Decision Audit tab shows full trace table with expandable phase breakdown.

### 6. Human-in-the-Loop Gates
Trust starts at 0.5 (neutral) and adjusts: +0.05 per success, -0.10 per failure. High-stakes actions (alerts at 0.6, escalations at 0.7) require trust above threshold. Sidebar shows trust gauge; emergency responses show approval buttons.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Streamlit UI                       │
│  Chat · Dashboard · History · Monitor · Decision Audit│
│  Trust Gauge · Budget Gauge · Automation Rules        │
└─────────────┬───────────────────────────────────────┘
              │
┌─────────────▼───────────────────────────────────────┐
│                   LLMAgent (ReAct)                    │
│  plan → execute → reflect → synthesize               │
│  + continuous learning patterns                       │
│  + cost-aware model routing                           │
│  + circuit breaker protection                         │
│  + structured trace collection                        │
│  + trust-gated approval                               │
└──┬──────────┬──────────┬──────────┬─────────────────┘
   │          │          │          │
┌──▼──┐  ┌───▼───┐  ┌───▼───┐  ┌──▼──────────┐
│Quick│  │ Deep  │  │Emerg. │  │ ChainAgent  │
│Agent│  │ Agent │  │ Agent │  │ (Fallback)  │
└──┬──┘  └───┬───┘  └───┬───┘  └─────────────┘
   │         │          │
┌──▼─────────▼──────────▼───────────────────────────┐
│              FortyGuard API Client                   │
│  env_params · heatmap · heat_intelligence           │
│  satellite · streetview · credits                   │
└────────────────────────────────────────────────────┘
```

## What Judges Will See

| Criteria | HeatMind |
|---|---|
| **Autonomous action** | Multi-agent system plans, tools, reflects, delegates, alerts — without human approval |
| **Cost awareness** | Budget-gated routing, visible cost ledger, agent prefers cheaper paths when sufficient |
| **Self-healing** | Circuit breaker detects degraded providers, auto-fallback, auto-recovery |
| **Continuous learning** | Patterns extracted from every analysis, injected into future planning |
| **Event-driven** | Rule engine fires actions on conditions, not just user queries |
| **Decision accountability** | Full trace per decision: phases, cost, confidence, outcome, delegations |
| **Trust evolution** | Starts cautious (asks approval), earns autonomy over time |
| **Production readiness** | 577+ tests, Docker, CI/CD, multi-channel alerts, graceful degradation |

## Demo

**Live:** [heatmind.streamlit.app](https://heatmind.streamlit.app)

### Quick Demo (2 minutes)
1. **Chat tab:** Ask "What's the heat index in Dubai right now?" → Watch the agent plan, call tools, reflect, answer. Open Monitor tab for cost breakdown.
2. **Monitor tab:** See Automation Rules with toggle switches, LLM Health indicators, Lessons Learned patterns.
3. **Decision Audit tab:** Click a trace to see per-phase cost and latency breakdown.
4. **Sidebar:** Watch the Trust Score gauge — approve/reject emergency responses to see it change.

### Emergency Drill (3 minutes)
1. Ask "Run a simulated emergency drill for Phoenix" → Watch the full autonomous chain: coordinator → emergency coordinator → public alert.
2. Trust gate appears if trust < 0.7 → click Approve/Reject → watch trust score update.
3. Check Decision Audit for the complete trace with 4+ spans.

### Local Demo
```bash
git clone https://github.com/sudo-robi/heatmind.git
cd heatmind
pip install -r requirements.txt
cp .env.example .env  # add your API keys
streamlit run streamlit_app.py
```

## Tech Stack

- **Language:** Python 3.14
- **LLM:** Gemini 3.6 Flash (with OpenAI/Anthropic/Ollama/Mock fallback)
- **API:** FortyGuard Temperature API (all 6 endpoints, async polling)
- **UI:** Streamlit with dark theme, SVG icons, live gauges
- **Storage:** MongoDB (with in-memory fallback)
- **Testing:** pytest, 577+ tests, CI/CD via GitHub Actions
- **Deployment:** Streamlit Cloud (auto-deploy from main)

## File Structure

```
heatmind/
├── agents/                 # Agent implementations
│   ├── llm_agent.py       # Core ReAct reasoning loop
│   ├── chain_agent.py     # Deterministic fallback
│   ├── emergency_agent.py # Emergency response specialist
│   ├── nlp_parser.py      # Query parsing
│   └── router.py          # Query routing
├── api/                   # FortyGuard API client
│   └── fortyguard.py      # All 6 endpoints + credit tracking
├── automation/            # Event-driven automation
│   ├── rules.py           # Rule engine with condition evaluation
│   └── scheduler.py       # Rule evaluation on monitor checks
├── memory/                # Memory and learning
│   ├── session.py         # Session memory + pattern storage
│   └── learning.py        # Pattern extraction and aggregation
├── monitor/               # Continuous monitoring
│   └── loop.py            # Monitor loop with zone checks
├── utils/                 # Utilities
│   ├── llm.py             # LLM provider abstraction + routing
│   ├── cost_ledger.py     # Cost tracking + budget management
│   ├── agent_circuit_breaker.py  # Self-healing circuit breaker
│   ├── trace.py           # Structured evidence trail
│   ├── trust.py           # Trust scoring engine
│   ├── alerts.py          # Multi-channel alert dispatch
│   ├── metrics.py         # Performance metrics
│   └── personas.py        # Agent system prompts
├── tests/                 # 577+ tests
├── streamlit_app.py       # Main UI (Chat, Dashboard, Monitor, Audit)
├── main.py                # CLI entry point
├── config.py              # Configuration (env + Streamlit secrets)
├── requirements.txt       # Python dependencies
├── Dockerfile             # Container deployment
└── SUBMISSION_SUMMARY.md  # This file
```

---

*Built for FortyGuard Hackathon'26 — Because every degree matters.*
