<div align="center">

```
  ╔══════════════════════════════════════════════════════════════════╗
  ║                                                                ║
  ║     🔥🔥🔥    H E A T M I N D    🔥🔥🔥                       ║
  ║                                                                ║
  ║     Multi-Agent Heat Intelligence System                       ║
  ║     Powered by FortyGuard Temperature API                      ║
  ║                                                                ║
  ║     "Autonomous monitoring. Intelligent alerts. Lives saved."  ║
  ║                                                                ║
  ╚══════════════════════════════════════════════════════════════════╝
```

**Heat kills thousands every year. HeatMind stops it before it starts.**

A conversational, autonomous heat monitoring and emergency response platform
that routes queries to specialized AI agents, remembers context across sessions,
and triggers multi-channel alerts when conditions become dangerous.

**[Live Demo →](https://heatmind.streamlit.app)** | [GitHub Repo →](https://github.com/sudo-robi/heatmind)

[![Python 3.14](https://img.shields.io/badge/Python-3.14-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![MongoDB](https://img.shields.io/badge/MongoDB-7-47A248?style=for-the-badge&logo=mongodb&logoColor=white)](https://mongodb.com)
[![FortyGuard](https://img.shields.io/badge/FortyGuard-API-E63946?style=for-the-badge)](https://fortyguard.io)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.0-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
[![MCP](https://img.shields.io/badge/MCP-Compatible-8B5CF6?style=for-the-badge)](https://modelcontextprotocol.io)
[![Tests](https://img.shields.io/badge/Tests-460+-00C853?style=for-the-badge)](https://pytest.org)
[![Coverage](https://img.shields.io/badge/Coverage-90%25-FFD600?style=for-the-badge)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-00BFA5?style=for-the-badge)](LICENSE)

---

</div>

## Why HeatMind?

| Traditional Systems | HeatMind |
|---|---|
| ❌ No memory — each query starts fresh | ✅ **Session Memory** — remembers past events, decisions, outcomes |
| ❌ No intelligence — raw numbers, no context | ✅ **AI Analysis** — risk assessment, severity levels, recommendations |
| ❌ No autonomy — humans manually check dashboards | ✅ **Autonomous Response** — 24/7 monitoring, instant multi-channel alerts |
| ❌ No integration — siloed data | ✅ **MCP Ready** — exposes tools to Claude, GPT, Gemini via Model Context Protocol |

---

## Features

| Feature | Description |
|:---|:---|
| 🧠 **Intelligent Query Routing** | Natural language queries classified by complexity and urgency, routed to the optimal agent |
| 🔄 **5 Agentic Patterns** | Session Memory, Query Router, Autonomous Monitor, Conversational Context, Emergency Response |
| 🌐 **Dual Interface** | Full-featured CLI for developers + Streamlit GUI with real-time dashboard |
| 🔔 **Multi-Channel Alerts** | Console, Slack, Email, Webhook — triggered autonomously when thresholds are exceeded |
| 🗄️ **Persistent Memory** | MongoDB-backed session memory with UUID tracking, conversation history, and TTL expiration |
| 🔌 **MCP Integration** | Exposes 5 MCP tools so external AI agents can query heat intelligence |
| 📊 **Live Dashboard** | Agent distribution, response times, sentiment analysis, session history |
| 🐳 **Docker Ready** | One command to launch the full stack (App + MongoDB) |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          HEATMIND SYSTEM                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌─────────────┐    ┌──────────────┐    ┌─────────────────────────┐  │
│   │             │    │              │    │                         │  │
│   │  CLI / GUI  │───▶│ Query Router │───▶│   Agent Selection       │  │
│   │  (User)     │    │              │    │                         │  │
│   │             │    │ • Complexity │    │  ┌──────────┐           │  │
│   └─────────────┘    │ • Urgency    │    │  │  Quick   │ ◀─ Simple │  │
│                      │ • Confidence │    │  │  Agent   │  queries  │  │
│                      └──────────────┘    │  └──────────┘           │  │
│                                          │  ┌──────────┐           │  │
│                                          │  │  Deep    │ ◀─ Complex│  │
│                                          │  │  Agent   │  queries  │  │
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
│                                          │   • Conversations   │      │
│                                          │   • Decisions       │      │
│                                          │   • Events          │      │
│                                          │   • Zone History    │      │
│                                          └─────────────────────┘      │
│                                                     │                  │
│   ┌──────────────────────────────────────────────┐  │                  │
│   │          FortyGuard Temperature API           │  │                  │
│   │  ┌──────────┐ ┌──────────┐ ┌──────────┐     │  │                  │
│   │  │ Heatmap  │ │Env Params│ │ Heat Intel│     │  │                  │
│   │  └──────────┘ └──────────┘ └──────────┘     │  │                  │
│   │  ┌──────────┐ ┌──────────┐                   │  │                  │
│   │  │Satellite │ │Streetview│                   │  │                  │
│   │  └──────────┘ └──────────┘                   │  │                  │
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
│   │                      Alert System                             │   │
│   │  Console │ Slack │ Webhook │ Email │ MCP Server               │   │
│   └───────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## The Five Agentic Patterns

HeatMind demonstrates **five distinct agentic AI patterns**, each solving a specific challenge:

### 1. Session Memory — Persistence

```
┌─────────────────────────────────────────────────────┐
│ Turn 1: "What's the heat in Dubai?"                 │
│        → Stored: {location: Dubai, query: heat}     │
├─────────────────────────────────────────────────────┤
│ Turn 2: "What about Abu Dhabi?"                     │
│        → Stored: {location: Abu Dhabi, query: heat} │
├─────────────────────────────────────────────────────┤
│ Turn 3: "Compare both cities"                       │
│        → Recalled: Dubai + Abu Dhabi data           │
├─────────────────────────────────────────────────────┤
│ Turn 4: "Start monitoring both"                     │
│        → Recalled: Both locations, started monitor  │
└─────────────────────────────────────────────────────┘
```

MongoDB-backed session persistence with UUID tracking, conversation history, and TTL-based expiration.

### 2. Query Router — Intelligent Routing

```
"What's the temperature?"
├── Complexity: SIMPLE (0.7 confidence)
├── Urgency: LOW
└── Route: Quick Agent → env_params endpoint

"Give me a full heat risk assessment for Dubai"
├── Complexity: COMPLEX (0.85 confidence)
├── Urgency: MEDIUM
└── Route: Deep Agent → env_params + heatmap + intel

"EMERGENCY: Workers collapsing in Phoenix!"
├── Complexity: MODERATE (0.9 confidence)
├── Urgency: CRITICAL
└── Route: Emergency Agent → alert + recommendations
```

Multi-factor classification (complexity × urgency) with confidence scoring. Simple queries use lightweight endpoints; complex queries trigger comprehensive analysis; critical queries bypass analysis and trigger immediate alerts.

### 3. Autonomous Monitor — Scheduled Intelligence

```
┌──────────┐     ┌──────────┐     ┌──────────────────┐
│  CronJob │────▶│  Check   │────▶│  Threshold       │
│  (30min) │     │  Zones   │     │  Detection       │
└──────────┘     └──────────┘     └────────┬─────────┘
                                    ┌───────▼─────────┐
                                    │ Emergency Agent  │
                                    │ + Alert System   │
                                    └─────────────────┘
```

Scheduled polling loop monitors configured zones, compares readings against thresholds, and triggers autonomous emergency responses.

### 4. Conversational Context — Context Awareness

```
User: "What's the heat in Dubai?"
Bot:  "Heat Index: 42C"
[Stored: {location: Dubai, last_query: heat}]

User: "What about tomorrow?"
Bot:  [Recalled: Dubai location, queries tomorrow's data]
[Stored: {date: tomorrow, last_query: forecast}]

User: "Start monitoring this location"
Bot:  [Recalled: Dubai coordinates, started monitor]
```

Per-session conversation history stored in MongoDB. Agents receive full conversation context, enabling multi-turn reasoning without re-explaining context.

### 5. Emergency Response — Autonomous Action

```
Threshold Exceeded
    │
    ▼
┌──────────────────┐
│ Assess Severity  │ extreme / dangerous / emergency / warning
└────────┬─────────┘
         │
    ┌────▼────┐
    │ Alert   │
    │ System  │
    └────┬────┘
         │
         ├──▶ Console Alert
         ├──▶ Slack Notification
         ├──▶ Webhook (Discord/Custom)
         └──▶ Email Alert
```

The monitor loop detects anomalies and triggers the Emergency Agent, which fans out alerts to all configured channels within seconds.

---

## Quick Start

### Prerequisites

- Python 3.14
- MongoDB (local or Atlas)
- FortyGuard API key

### One-Command Setup

```bash
git clone https://github.com/sudo-robi/heatmind.git && \
cd heatmind && \
python -m venv venv && \
source venv/bin/activate && \
pip install -r requirements.txt && \
cp .env.example .env && \
docker run -d --name heatmind-mongo -p 27017:27017 mongo:7 && \
python main.py
```

### Step-by-Step Setup

```bash
# 1. Clone
git clone https://github.com/sudo-robi/heatmind.git
cd heatmind

# 2. Virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your API key and MongoDB URI

# 5. Start MongoDB
docker run -d --name heatmind-mongo -p 27017:27017 mongo:7

# 6. Run CLI
python main.py

# 7. OR run GUI
streamlit run streamlit_app.py
```

---

## Agent Pipeline

```
User Input
    │
    ▼
┌──────────────────┐
│ Parse Location   │  Extract lat/lng from query or use default
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Route Query      │  Classify complexity + urgency
└────────┬─────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌────────┐
│ Simple │ │Complex │
│        │ │        │
└───┬────┘ └───┬────┘
    │           │
    ▼           ▼
┌──────────────────┐
│ Execute Agent    │  Call FortyGuard API endpoints
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Store Memory     │  Save to MongoDB (session, events, decisions)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Format Response  │  Human-readable output with recommendations
└────────┬─────────┘
         │
         ▼
User Output
```

---

## MCP Integration

HeatMind exposes **5 MCP tools** via the Model Context Protocol, allowing external AI agents (Claude, GPT, Gemini) to query heat intelligence:

| MCP Tool | Description |
|---|---|
| `query_heat_conditions` | Get current heat index, humidity, AQI for a location |
| `deep_heat_analysis` | Comprehensive risk assessment with heatmap + intelligence report |
| `emergency_heat_check` | Check for emergency conditions, trigger alerts if threshold exceeded |
| `route_query` | Classify a natural language query and return routing decision |
| `get_session_history` | Retrieve conversation history for a session |

### Running as MCP Server

```bash
python -m utils.mcp_client serve
```

### Using as MCP Client

```python
from utils.mcp_client import HeatMindMCPClient

client = HeatMindMCPClient()
result = client.query("What's the heat index in Dubai?")
print(result)
```

### MCP Tool List

```
$ python -m utils.mcp_client
HeatMind MCP Client
Available tools:
  - query_heat_conditions: Get current heat conditions for a location
  - deep_heat_analysis: Comprehensive heat risk assessment
  - emergency_heat_check: Check for emergency heat conditions
  - route_query: Classify a natural language query
  - get_session_history: Retrieve conversation history
```

---

## Slack & Email Alerts

HeatMind ships with a **multi-channel alert system** that triggers automatically when the autonomous monitor detects threshold violations.

### Slack Setup

1. Create a Slack App → Incoming Webhooks → Add to Workspace
2. Copy the webhook URL
3. Set in `.env`:

```env
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX
```

**Alert format:**
```
🌡️ HeatMind Alert — DANGEROUS
├── Zone: Abu Dhabi Central
├── Heat Index: 52°C
├── Severity: DANGEROUS
├── Time: 2026-08-17T12:00:00Z
└── Recommended Actions:
    • Evacuate outdoor workers immediately
    • Open all available cooling centers
    • Issue public heat emergency warning
```

### Email Setup

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_app_password
ALERT_EMAIL_TO=alerts@yourcompany.com
```

### Webhook Setup (Discord/Custom)

```env
ALERT_WEBHOOK_URL=https://discord.com/api/webhooks/XXXXX/YYYYY
```

All channels fire simultaneously — no single point of failure.

---

## API Endpoints

HeatMind uses **all 6 FortyGuard Temperature API endpoints**:

| Endpoint | Purpose | HeatMind Feature | Agent |
|---|---|---|---|
| `/v1/env_params` | Heat index, AQI, humidity, solar | Simple queries | Quick |
| `/v1/heatmap` | Thermal maps — snapshot, exceedance | Deep analysis | Deep |
| `/v1/heat_intel` | Multi-dimensional intelligence reports | Risk assessment | Deep |
| `/v1/satellite` | Satellite view segmentation | Ground truth | Deep |
| `/v1/streetview` | Ground-level visual verification | Visual confirm | Deep |

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Language** | Python 3.14 | Core runtime |
| **Database** | MongoDB 7 | Session memory, conversation history |
| **API** | FortyGuard Temperature API | Real-time heat data, heatmaps, intelligence reports |
| **CLI** | Rich | Terminal UI with colors and formatting |
| **GUI** | Streamlit | Web interface with real-time dashboard |
| **Alerts** | Slack / SMTP / Webhooks | Multi-channel emergency notifications |
| **Integration** | MCP (Model Context Protocol) | Exposes tools to external AI agents |
| **Testing** | pytest + coverage | 460 tests, 90%+ code coverage |
| **CI/CD** | GitHub Actions | Automated testing and deployment |
| **Deployment** | Docker + Docker Compose | Containerized full-stack deployment |

---

## Project Structure

```
heatmind/
├── main.py                    # CLI entry point
├── streamlit_app.py           # Streamlit web interface
├── config.py                  # Configuration management
├── requirements.txt           # Python dependencies
├── .env.example               # Environment template
├── Dockerfile                 # Container deployment
├── docker-compose.yml         # Full stack setup
│
├── api/
│   └── fortyguard.py          # FortyGuard API client (all 6 endpoints)
│
├── agents/
│   ├── router.py              # Query classification (complexity + urgency)
│   ├── quick_agent.py         # Simple queries (env_params)
│   ├── deep_agent.py          # Complex analysis (heatmap + intel)
│   └── emergency_agent.py     # Critical alerts (threshold + recommendations)
│
├── memory/
│   └── session.py             # MongoDB session memory (UUID, messages, TTL)
│
├── monitor/
│   └── loop.py                # Scheduled monitoring loop
│
├── utils/
│   ├── alerts.py              # Console + Slack + webhook + email alerts
│   └── mcp_client.py          # MCP server + client integration
│
├── tests/                     # 460 tests (90%+ coverage)
│   ├── conftest.py
│   ├── test_config.py
│   ├── test_router.py
│   ├── test_session.py
│   ├── test_agents.py
│   ├── test_api.py
│   ├── test_monitor.py
│   ├── test_alerts.py
│   └── test_integration.py
│
└── .github/
    └── workflows/
        └── ci.yml             # GitHub Actions CI/CD
```

---

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=. --cov-report=term-missing

# Run specific test suites
pytest tests/test_router.py -v      # Query routing
pytest tests/test_agents.py -v      # Agent logic
pytest tests/test_session.py -v     # Session memory
pytest tests/test_monitor.py -v     # Monitor loop
pytest tests/test_alerts.py -v      # Alert system
pytest tests/test_integration.py -v # End-to-end flows
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
| `monitor/loop.py` | 89% |

---

## Docker Deployment

### Docker Compose (Recommended)

```bash
# Start all services (App + MongoDB)
docker-compose up -d

# View logs
docker-compose logs -f heatmind

# Stop all services
docker-compose down
```

### Manual Docker

```bash
# Build image
docker build -t heatmind .

# Run with MongoDB
docker run -d --name heatmind-mongo -p 27017:27017 mongo:7
docker run -d --name heatmind-app -p 8501:8501 \
  -e MONGO_URI=mongodb://host.docker.internal:27017 \
  -e FORTYGUARD_API_KEY=your_key \
  heatmind
```

---

## Environment Variables

```env
# ━━━ Required ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORTYGUARD_API_KEY=your_api_key_here

# ━━━ MongoDB ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MONGO_URI=mongodb://localhost:27017
MONGO_DB=heatmind

# ━━━ Slack Alerts (optional) ━━━━━━━━━━━━━━━━━━━━━
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# ━━━ Email Alerts (optional) ━━━━━━━━━━━━━━━━━━━━━
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_app_password
ALERT_EMAIL_TO=recipient@example.com

# ━━━ Webhook Alerts (optional) ━━━━━━━━━━━━━━━━━━━
ALERT_WEBHOOK_URL=https://your-webhook-url.com/alerts

# ━━━ Monitor Settings ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MONITOR_INTERVAL_MINUTES=30
HEAT_THRESHOLD_C=40
HEAT_INDEX_THRESHOLD=45
```

---

## Industry Use Cases

| Sector | Application |
|---|---|
| 🏗️ **Construction** | Monitor outdoor worker heat exposure in real-time |
| 🎪 **Public Events** | Track heat conditions at stadiums, festivals, outdoor venues |
| 🌾 **Agriculture** | Protect crops and workers from heat damage |
| 🏙️ **Urban Planning** | Identify heat islands and plan interventions |
| 🚑 **Emergency Services** | Real-time heat intelligence for first responders |
| 🏢 **Facility Management** | Monitor HVAC load and outdoor conditions |

---

## Why HeatMind Wins

1. **Real-World Impact** — Heat-related incidents kill thousands annually. HeatMind provides autonomous monitoring and emergency response that saves lives.

2. **Complete Agentic Architecture** — Five distinct agentic patterns working together — not just one pattern, but a complete multi-agent system.

3. **Production-Ready** — 460 tests, 90%+ coverage, GitHub Actions CI/CD, Docker deployment, MongoDB Atlas support, multi-channel alerts.

4. **Natural Language Interface** — Users ask questions in plain English. The system routes, reasons, and responds intelligently.

5. **Autonomous Intelligence** — The monitor loop runs 24/7, detecting anomalies and triggering emergency responses without human intervention.

6. **Dual Interface** — Full-featured CLI for developers + Streamlit GUI for visual interaction.

7. **MCP Compatible** — Exposes heat intelligence as MCP tools, making HeatMind composable with any AI agent ecosystem.

---

## Contributing

Contributions are welcome! Here's how to get started:

```bash
# Fork the repository
git clone https://github.com/your-username/heatmind.git
cd heatmind

# Create a feature branch
git checkout -b feature/amazing-feature

# Install dev dependencies
pip install -r requirements.txt

# Make changes and run tests
pytest tests/ -v

# Commit and push
git commit -m "Add amazing feature"
git push origin feature/amazing-feature

# Open a Pull Request
```

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and development process.

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Built for FortyGuard Hackathon'26 — Track 06: Agentic AI**

```
🔥 HeatMind — Because every degree matters. 🔥
```

</div>
