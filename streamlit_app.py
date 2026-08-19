import contextlib
import json
import os
import sys
import time
import uuid
from collections import Counter
from datetime import UTC, datetime

import streamlit as st

sys.path.insert(0, os.path.dirname(__file__))

import config as _config
from agents.deep_agent import DeepAgent
from agents.emergency_agent import EmergencyAgent
from agents.quick_agent import QuickAgent
from agents.router import route_query
from config import HEAT_INDEX_THRESHOLD, HEAT_THRESHOLD_C, MONITOR_INTERVAL_MINUTES
from memory.session import SessionMemory

FORTYGUARD_API_KEY = _config.FORTYGUARD_API_KEY
if not FORTYGUARD_API_KEY:
    with contextlib.suppress(Exception):
        FORTYGUARD_API_KEY = st.secrets.get("FORTYGUARD_API_KEY", "")
if FORTYGUARD_API_KEY:
    _config.FORTYGUARD_API_KEY = FORTYGUARD_API_KEY

SVG = {
    "fire": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/></svg>',
    "brain": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588A4 4 0 1 0 12 18Z"/><path d="M12 5a3 3 0 1 1 5.997.125 4 4 0 0 1 2.526 5.77 4 4 0 0 1-.556 6.588A4 4 0 1 1 12 18Z"/></svg>',
    "shield": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/></svg>',
    "zap": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z"/></svg>',
    "database": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5V19A9 3 0 0 0 21 19V5"/><path d="M3 12A9 3 0 0 0 21 12"/></svg>',
    "monitor": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="20" height="14" x="2" y="3" rx="2"/><line x1="8" x2="16" y1="21" y2="21"/><line x1="12" x2="12" y1="17" y2="21"/></svg>',
    "chat": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7.9 20A9 9 0 1 0 4 16.1L2 22z"/></svg>',
    "activity": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2"/></svg>',
    "download": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/></svg>',
    "trash": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>',
    "plus": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="M12 5v14"/></svg>',
    "refresh": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/></svg>',
    "map": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/></svg>',
    "thermometer": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 4v10.54a4 4 0 1 1-4 0V4a2 2 0 0 1 4 0Z"/></svg>',
    "check": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>',
    "chevron": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m9 18 6-6-6-6"/></svg>',
    "wifi": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h.01"/><path d="M2 8.82a15 15 0 0 1 20 0"/><path d="M5 12.859a10 10 0 0 1 14 0"/><path d="M8.5 16.429a5 5 0 0 1 7 0"/></svg>',
    "layers": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"/><path d="m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65"/><path d="m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"/></svg>',
    "target": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>',
    "search": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" x2="16.65" y1="21" y2="16.65"/></svg>',
    "siren": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 18v.6A6 6 0 0 0 13 24h1a6 6 0 0 0 6-6v-3"/><circle cx="12" cy="12" r="4"/><path d="M12 12h.01"/></svg>',
    "sparkles": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z"/></svg>',
    "alert": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>',
}

C = {
    "bg": "#0d1117",
    "surface": "#161b22",
    "surface_alt": "#1c2128",
    "border": "#30363d",
    "border_light": "#21262d",
    "text": "#e6edf3",
    "text_muted": "#b1bac4",
    "text_dim": "#6e7681",
    "accent": "#58a6ff",
    "accent_dim": "#1f6feb",
    "green": "#3fb950",
    "green_dim": "#238636",
    "yellow": "#d29922",
    "yellow_dim": "#9e6a03",
    "red": "#f85149",
    "red_dim": "#da3633",
    "orange": "#db6d28",
    "purple": "#bc8cff",
    "purple_dim": "#8957e5",
    "cyan": "#39d2c0",
}

st.set_page_config(
    page_title="HeatMind — Heat Intelligence System", page_icon="🔥", layout="wide", initial_sidebar_state="expanded"
)

st.markdown(
    f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');

/* ── Base ── */
.stApp {{ background: {C["bg"]}; font-family: 'Inter',-apple-system,sans-serif; color: {C["text"]}; }}
section[data-testid="stSidebar"] {{ background: {C["surface"]}; border-right: 1px solid {C["border"]}; }}
section[data-testid="stSidebar"] .stMarkdown h1,
section[data-testid="stSidebar"] .stMarkdown h2,
section[data-testid="stSidebar"] .stMarkdown h3 {{ color: {C["text"]} !important; }}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {{ gap:4px; background:{C["surface"]}; padding:6px; border-radius:10px; border:1px solid {C["border"]}; }}
.stTabs [data-baseweb="tab"] {{ background:transparent; color:{C["text_muted"]}; border-radius:6px; padding:10px 20px; font-weight:600; font-size:0.9rem; border:none; transition:all 0.2s ease; }}
.stTabs [data-baseweb="tab"]:hover {{ color:{C["text"]}; background:{C["border_light"]}; }}
.stTabs [aria-selected="true"] {{ background:{C["accent_dim"]} !important; color:#fff !important; box-shadow:0 2px 8px {C["accent_dim"]}40; }}
.stTabs [data-baseweb="tab-highlight"] {{ display:none; }}
.stTabs [data-baseweb="tab-border"] {{ display:none; }}

/* ── Chat ── */
.stChatMessage {{ background:{C["surface"]}; border-radius:12px; border:1px solid {C["border"]}; padding:16px; transition:border-color 0.2s ease; }}
.stChatMessage:hover {{ border-color:{C["border"]}; }}

/* ── Cards ── */
.metric-card {{ background:{C["surface"]}; border:1px solid {C["border"]}; border-radius:12px; padding:24px 16px; text-align:center; transition:all 0.25s ease; }}
.metric-card:hover {{ border-color:{C["accent"]}; transform:translateY(-2px); box-shadow:0 4px 16px rgba(0,0,0,0.3); }}
.metric-value {{ font-size:2.6rem; font-weight:800; color:{C["text"]}; line-height:1.1; font-family:'JetBrains Mono',monospace; }}
.metric-label {{ color:{C["text_muted"]}; font-size:0.82rem; margin-top:8px; font-weight:700; letter-spacing:0.5px; text-transform:uppercase; white-space:nowrap; }}
.zone-card {{ background:{C["surface"]}; border:1px solid {C["border"]}; border-radius:12px; padding:18px 20px; margin:8px 0; transition:all 0.25s ease; }}
.zone-card:hover {{ border-color:{C["accent"]}; transform:translateY(-1px); box-shadow:0 2px 12px rgba(0,0,0,0.2); }}
.zone-name {{ font-size:1.15rem; font-weight:800; color:{C["text"]}; }}
.zone-coords {{ color:{C["text_muted"]}; font-size:0.88rem; font-family:'JetBrains Mono',monospace; font-weight:500; }}

/* ── Section Headers ── */
.section-header {{ font-size:1.4rem; font-weight:800; color:{C["text"]}; margin:24px 0 14px 0; padding-bottom:10px; border-bottom:2px solid {C["border"]}; display:flex; align-items:center; gap:10px; }}

/* ── Processing Pipeline ── */
.processing-pipeline {{ display:flex; align-items:center; gap:8px; padding:12px 16px; background:{C["surface"]}; border:1px solid {C["border"]}; border-radius:10px; margin:8px 0; flex-wrap:wrap; }}
.pipeline-stage {{ display:inline-flex; align-items:center; gap:4px; padding:5px 12px; border-radius:8px; font-size:0.85rem; font-weight:700; transition:all 0.3s ease; }}
.pipeline-stage.active {{ animation:stagePulse 1.5s ease infinite; box-shadow:0 0 12px currentColor; }}
.pipeline-arrow {{ color:{C["text_dim"]}; }}

/* ── Metadata Tags ── */
.msg-meta {{ display:flex; flex-wrap:wrap; gap:6px; margin-top:8px; }}
.meta-tag {{ display:inline-flex; align-items:center; gap:4px; padding:4px 10px; border-radius:6px; font-size:0.8rem; font-weight:700; background:{C["border_light"]}; color:{C["text_muted"]}; border:1px solid {C["border"]}; }}
.sentiment-pill {{ display:inline-flex; align-items:center; gap:4px; padding:3px 10px; border-radius:12px; font-size:0.8rem; font-weight:700; transition:all 0.2s ease; }}

/* ── Timeline ── */
.timeline-item {{ border-left:3px solid {C["accent"]}; padding:12px 16px; margin:8px 0; background:{C["surface"]}; border-radius:0 10px 10px 0; transition:border-color 0.2s ease; }}
.timeline-item:hover {{ border-left-color:{C["green"]}; }}
.timeline-time {{ color:{C["text_muted"]}; font-size:0.85rem; }}
.timeline-content {{ color:{C["text"]}; margin-top:4px; font-size:0.95rem; line-height:1.5; }}

/* ── Alerts ── */
.alert-card {{ background: linear-gradient(135deg, {C["red_dim"]}, {C["red"]}20); border:1px solid {C["red"]}; border-radius:12px; padding:24px; color:#fff; font-size:1rem; }}
.alert-card-clear {{ background: linear-gradient(135deg, {C["green_dim"]}, {C["green"]}20); border:1px solid {C["green"]}; border-radius:12px; padding:24px; color:#fff; font-size:1rem; }}
.escalation-banner {{ background: linear-gradient(135deg, {C["red_dim"]}, {C["red"]}30); border:1px solid {C["red"]}; border-radius:12px; padding:20px; color:#fff; margin:12px 0; border-left:4px solid {C["red"]}; animation:fadeSlideIn 0.3s ease; font-size:1rem; }}

/* ── Session ID ── */
.session-id {{ background:{C["border_light"]}; border:1px solid {C["border"]}; border-radius:8px; padding:8px 12px; font-family:'JetBrains Mono',monospace; font-size:0.85rem; color:{C["text_muted"]}; font-weight:600; }}

/* ── Hero ── */
.hero-container {{ position:relative; overflow:hidden; padding:48px 0 24px 0; background: linear-gradient(180deg, {C["surface"]}80 0%, transparent 100%); border-radius:16px; margin-bottom:8px; }}
.heat-particle {{ position:absolute; border-radius:50%; animation:floatUp linear infinite; opacity:0; }}

/* ── Animations ── */
@keyframes floatUp {{ 0%{{transform:translateY(100px) scale(0);opacity:0;}} 10%{{opacity:0.7;}} 90%{{opacity:0.2;}} 100%{{transform:translateY(-200px) scale(1);opacity:0;}} }}
@keyframes fadeSlideIn {{ 0%{{opacity:0;transform:translateY(8px);}} 100%{{opacity:1;transform:translateY(0);}} }}
@keyframes stagePulse {{ 0%,100%{{opacity:0.7;}} 50%{{opacity:1;}} }}
@keyframes shimmer {{ 0%{{background-position:-200% 0;}} 100%{{background-position:200% 0;}} }}

/* ── Buttons ── */
.stButton > button {{ background:{C["surface"]}; color:{C["text"]}; border:1px solid {C["border"]}; border-radius:8px; padding:8px 16px; font-weight:600; font-size:0.85rem; transition:all 0.2s ease; }}
.stButton > button:hover {{ border-color:{C["accent"]}; color:{C["accent"]}; transform:translateY(-1px); box-shadow:0 2px 8px rgba(0,0,0,0.2); }}
button[kind="primary"] {{ background:{C["accent_dim"]} !important; color:#fff !important; border:1px solid {C["accent"]} !important; }}
button[kind="primary"]:hover {{ background:{C["accent"]} !important; box-shadow:0 4px 12px {C["accent_dim"]}60; }}

/* ── Inputs ── */
.stTextInput > div > div > input, .stNumberInput > div > div > input {{ background:{C["border_light"]}; border:1px solid {C["border"]}; border-radius:8px; color:{C["text"]}; transition:border-color 0.2s ease; }}
.stTextInput > div > div > input:focus {{ border-color:{C["accent"]}; box-shadow:0 0 0 2px {C["accent_dim"]}30; }}

/* ── Dividers ── */
hr {{ border-color:{C["border"]}; opacity:0.5; }}

/* ── Hide defaults ── */
#MainMenu {{ visibility:hidden; }} footer {{ visibility:hidden; }} header {{ visibility:hidden; }}

/* ── Error/Troubleshoot ── */
.error-box {{ background:{C["surface"]}; border:1px solid {C["border"]}; border-radius:10px; padding:16px; margin:8px 0; }}
.troubleshoot {{ background:{C["border_light"]}; border-left:3px solid {C["accent"]}; border-radius:0 8px 8px 0; padding:10px 14px; margin:8px 0; font-size:0.85rem; }}

/* ── Scrollbar ── */
::-webkit-scrollbar {{ width:6px; }}
::-webkit-scrollbar-track {{ background:{C["bg"]}; }}
::-webkit-scrollbar-thumb {{ background:{C["border"]}; border-radius:3px; }}
::-webkit-scrollbar-thumb:hover {{ background:{C["text_dim"]}; }}

/* ── Progress bar ── */
.stProgress > div > div {{ background:{C["border_light"]}; border-radius:4px; }}
</style>""",
    unsafe_allow_html=True,
)


def svg(name):
    return SVG.get(name, "")


def render_hero():
    colors = [C["red"], C["orange"], C["yellow"], C["accent"], C["purple"]]
    particles = ""
    for i in range(16):
        c = colors[i % len(colors)]
        left = 3 + (i * 6.5) % 94
        delay = (i * 0.6) % 5
        dur = 2.5 + (i % 4)
        size = 3 + (i % 6)
        particles += f'<div class="heat-particle" style="left:{left}%;bottom:0;width:{size}px;height:{size}px;background:{c};animation-delay:{delay}s;animation-duration:{dur}s;"></div>'
    st.markdown(
        f"""<div class="hero-container">{particles}
    <div style="position:relative;z-index:1;text-align:center;padding:24px 0;">
        <div style="display:flex;justify-content:center;align-items:center;gap:14px;margin-bottom:10px;">
            <span style="color:{C["red"]};filter:drop-shadow(0 0 8px {C["red"]}80);">{svg("fire")}</span>
            <span style="font-size:2.8rem;font-weight:800;color:{C["text"]};letter-spacing:-1.5px;background:linear-gradient(135deg,{C["text"]},{C["accent"]});-webkit-background-clip:text;-webkit-text-fill-color:transparent;">HeatMind</span>
            <span style="color:{C["orange"]};filter:drop-shadow(0 0 8px {C["orange"]}80);">{svg("brain")}</span>
        </div>
        <div style="color:{C["text_muted"]};font-size:1.15rem;font-weight:600;letter-spacing:0.3px;">Multi-Agent Heat Intelligence System</div>
        <div style="margin-top:14px;">
            <span style="display:inline-flex;align-items:center;gap:6px;padding:6px 14px;background:{C["surface"]};border:1px solid {C["border"]};border-radius:8px;font-size:0.88rem;font-weight:600;color:{C["text_muted"]};">{svg("shield")} Powered by FortyGuard Temperature API</span>
        </div>
    </div></div>""",
        unsafe_allow_html=True,
    )


STAGES = [
    {"key": "classifying", "emoji": "🔍", "color": C["cyan"], "text": "Classifying query type..."},
    {"key": "routing", "emoji": "🎯", "color": C["purple"], "text": "Routing to optimal agent..."},
    {"key": "analyzing", "emoji": "🧠", "color": C["accent"], "text": "Analyzing heat data..."},
    {"key": "processing", "emoji": "⚡", "color": C["orange"], "text": "Processing with AI model..."},
    {"key": "sentiment", "emoji": "💬", "color": C["cyan"], "text": "Analyzing response..."},
    {"key": "complete", "emoji": "✅", "color": C["green"], "text": "Response ready"},
    {"key": "escalating", "emoji": "🚨", "color": C["red"], "text": "Escalating to human agent..."},
]


def render_processing_status(active_key):
    html = '<div class="processing-pipeline">'
    for s in STAGES:
        active = "active" if s["key"] == active_key else ""
        opacity = "1" if s["key"] == active_key else "0.35"
        html += f'<span class="pipeline-stage {active}" style="background:{s["color"]}20;color:{s["color"]};border:1px solid {s["color"]}40;opacity:{opacity};">{s["emoji"]} {s["key"].title()}</span>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def cycling_processing(placeholder, escalate=False):
    keys = ["classifying", "routing", "analyzing", "processing", "sentiment"]
    if escalate:
        keys.append("escalating")
    keys.append("complete")
    for k in keys:
        with placeholder.container():
            render_processing_status(k)
            info = next((s for s in STAGES if s["key"] == k), None)
            if info:
                st.caption(f"{info['emoji']} {info['text']}")


def get_sentiment(score):
    if score is None:
        return "😐", "neutral", C["text_muted"]
    if score > 0.5:
        return "😊", "very positive", C["green"]
    if score > 0.2:
        return "🙂", "positive", C["green"]
    if score > 0.05:
        return "😐", "slightly positive", C["cyan"]
    if score < -0.5:
        return "😠", "very negative", C["red"]
    if score < -0.2:
        return "😕", "negative", C["orange"]
    if score < -0.05:
        return "😐", "slightly negative", C["yellow"]
    return "😐", "neutral", C["text_muted"]


def render_msg_metadata(msg):
    cols = st.columns(4)
    with cols[0]:
        s = msg.get("sentiment_score")
        if s is not None:
            e, l, c = get_sentiment(s)
            st.markdown(
                f'<div class="sentiment-pill" style="background:{c}15;color:{c};border:1px solid {c}40;">{e} {l} ({s:.2f})</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="sentiment-pill" style="background:{C["border_light"]};color:{C["text_dim"]};border:1px solid {C["border"]};">— sentiment</div>',
                unsafe_allow_html=True,
            )
    with cols[1]:
        agent = msg.get("agent", "—")
        ac = {"quick": C["green"], "deep": C["purple"], "emergency": C["red"]}.get(agent, C["text_muted"])
        st.markdown(
            f'<div class="sentiment-pill" style="background:{ac}15;color:{ac};border:1px solid {ac}40;">{svg("layers")} {agent}</div>',
            unsafe_allow_html=True,
        )
    with cols[2]:
        rt = msg.get("response_time_ms")
        if rt is not None:
            tc = C["green"] if rt < 500 else C["yellow"] if rt < 2000 else C["red"]
            st.markdown(
                f'<div class="sentiment-pill" style="background:{tc}15;color:{tc};border:1px solid {tc}40;">⏱ {rt:.0f}ms</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="sentiment-pill" style="background:{C["border_light"]};color:{C["text_dim"]};border:1px solid {C["border"]};">— time</div>',
                unsafe_allow_html=True,
            )
    with cols[3]:
        cs = msg.get("complexity_score")
        if cs is not None:
            pct = cs * 100
            cc = C["red"] if pct > 80 else C["orange"] if pct > 50 else C["green"]
            label = "complex" if pct > 80 else "moderate" if pct > 50 else "simple"
            st.markdown(
                f'<div class="sentiment-pill" style="background:{cc}15;color:{cc};border:1px solid {cc}40;">{svg("brain")} {label} ({pct:.0f}%)</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="sentiment-pill" style="background:{C["border_light"]};color:{C["text_dim"]};border:1px solid {C["border"]};">— complexity</div>',
                unsafe_allow_html=True,
            )


def display_error(error_type, message, context=""):
    configs = {
        "CONNECTION_ERROR": {
            "icon": "🔌",
            "title": "Connection Error",
            "color": C["red"],
            "steps": [
                "Check if backend is running",
                "Verify network connection",
                "Check firewall settings",
                "Try again in moments",
            ],
        },
        "TIMEOUT_ERROR": {
            "icon": "⏱",
            "title": "Timeout Error",
            "color": C["yellow"],
            "steps": ["Request took too long", "Server may be under load", "Try a simpler query", "Try again"],
        },
        "API_ERROR": {
            "icon": "⚠",
            "title": "API Error",
            "color": C["orange"],
            "steps": ["API returned error", "Check API key config", "Verify endpoint", "Contact support"],
        },
    }
    cfg = configs.get(
        error_type,
        {"icon": "❌", "title": "Error", "color": C["red"], "steps": ["Unexpected error", "Please try again"]},
    )
    st.markdown(
        f'<div class="error-box" style="border-left:3px solid {cfg["color"]};"><div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;"><span style="font-size:1.2rem;">{cfg["icon"]}</span><strong style="color:{cfg["color"]};">{cfg["title"]}</strong></div><div style="color:{C["text_muted"]};font-size:0.9rem;">{message}</div></div>',
        unsafe_allow_html=True,
    )
    with st.expander("Troubleshooting Steps"):
        for i, step in enumerate(cfg["steps"], 1):
            st.markdown(f"**{i}.** {step}")
        if st.button("Retry", key=f"retry_{error_type}"):
            st.rerun()


def display_escalation_banner(reason, ticket_id):
    st.markdown(
        f'<div class="escalation-banner"><div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">{svg("siren")}<strong style="font-size:1.1rem;">ESCALATED TO HUMAN AGENT</strong></div><div style="margin:4px 0;"><strong>Reason:</strong> {reason}</div><div style="margin:4px 0;"><strong>Ticket ID:</strong> <code>{ticket_id}</code></div><div style="margin:4px 0;"><strong>Status:</strong> Priority handling requested</div><hr style="border-color:rgba(255,255,255,0.2);margin:8px 0;"><div style="font-style:italic;opacity:0.9;">A human support agent will review this conversation and respond as soon as possible.</div></div>',
        unsafe_allow_html=True,
    )


def render_escalation_panel():
    escalated = [m for m in st.session_state.messages if m.get("escalated")]
    if not escalated:
        return
    st.markdown(
        f'<div class="escalation-banner" style="text-align:center;"><strong>{svg("siren")} {len(escalated)} Active Escalation(s)</strong><div style="opacity:0.9;margin-top:4px;">Human agent intervention requested</div></div>',
        unsafe_allow_html=True,
    )
    for i, msg in enumerate(reversed(escalated)):
        with st.expander(
            f"🎫 Ticket #{i + 1}: {msg.get('escalation_reason', 'Unknown')} — {msg.get('ticket_id', 'N/A')[:8]}..."
        ):
            st.markdown(
                f"**Ticket ID:** `{msg.get('ticket_id', 'N/A')}`\n**Reason:** {msg.get('escalation_reason', 'Unknown')}\n**Query:** {msg.get('content', '')[:150]}..."
            )
            st.info("A human support agent will review this conversation and respond as soon as possible.")


def generate_metrics_export():
    am = [m for m in st.session_state.messages if m.get("role") == "assistant"]
    rt = [m.get("response_time_ms", 0) for m in am if m.get("response_time_ms")]
    ss = [m["sentiment_score"] for m in am if m.get("sentiment_score") is not None]
    cs = [m["complexity_score"] for m in am if m.get("complexity_score") is not None]
    ac = dict(Counter([m.get("agent", "unknown") for m in am]))
    ec = len([m for m in st.session_state.messages if m.get("escalated")])
    return {
        "export_timestamp": datetime.now(UTC).isoformat(),
        "session_id": st.session_state.session_id,
        "summary": {
            "total_queries": st.session_state.query_count,
            "total_messages": len(st.session_state.messages),
            "escalated": ec,
            "agents": ac,
        },
        "performance": {
            "avg_ms": sum(rt) / len(rt) if rt else 0,
            "min_ms": min(rt) if rt else 0,
            "max_ms": max(rt) if rt else 0,
            "escalation_pct": (ec / len(am) * 100) if am else 0,
        },
        "sentiment": {
            "avg": sum(ss) / len(ss) if ss else None,
            "positive": sum(1 for s in ss if s > 0.1),
            "neutral": sum(1 for s in ss if -0.1 <= s <= 0.1),
            "negative": sum(1 for s in ss if s < -0.1),
        },
        "complexity": {
            "avg": sum(cs) / len(cs) if cs else None,
            "high": sum(1 for s in cs if s > 0.8),
            "medium": sum(1 for s in cs if 0.3 <= s <= 0.8),
            "low": sum(1 for s in cs if s < 0.3),
        },
    }


def init_session():
    if "session_id" not in st.session_state:
        memory = SessionMemory()
        st.session_state.session_id = memory.create_session("streamlit_user")
        st.session_state.memory = memory
        st.session_state.messages = []
        st.session_state.last_location = {"latitude": 25.2048, "longitude": 55.2708, "zone": "Dubai"}
        st.session_state.query_count = 0
        st.session_state.alert_count = 0
        st.session_state.total_response_time_ms = 0.0
        st.session_state.agent_counts = {"quick": 0, "deep": 0, "emergency": 0}
        st.session_state.escalation_count = 0
        st.session_state.session_start = datetime.now(UTC)


def handle_query(query):
    memory = st.session_state.memory
    sid = st.session_state.session_id
    routing = route_query(query)
    loc = st.session_state.last_location
    params = {
        "latitude": loc["latitude"],
        "longitude": loc["longitude"],
        "date": datetime.now().strftime("%Y-%m-%d"),
        "zone": loc["zone"],
    }
    if not FORTYGUARD_API_KEY:
        return {
            "response": f"**Routed to:** {routing.agent} agent\n**Complexity:** {routing.complexity.value}\n**Urgency:** {routing.urgency.value}\n\nSet `FORTYGUARD_API_KEY` in `.env` to enable live data.",
            "agent": routing.agent,
            "complexity": routing.complexity.value,
            "response_time_ms": 0,
            "complexity_score": 0.5,
            "sentiment_score": 0.0,
        }
    start = time.time()
    try:
        agent = {"quick": QuickAgent, "deep": DeepAgent, "emergency": EmergencyAgent}.get(routing.agent, QuickAgent)()
        result = agent.handle(query, sid, params)
        ms = (time.time() - start) * 1000
        memory.log_decision(sid, query, routing.agent, routing.reasoning, "completed")
        return {
            "response": result.get("response", "No response."),
            "agent": routing.agent,
            "complexity": routing.complexity.value,
            "response_time_ms": ms,
            "complexity_score": 0.5,
            "sentiment_score": 0.1,
        }
    except Exception as e:
        return {
            "response": f"Error: {e}",
            "agent": routing.agent,
            "complexity": routing.complexity.value,
            "response_time_ms": (time.time() - start) * 1000,
            "complexity_score": 0,
            "sentiment_score": -0.5,
        }


def parse_location_from_query(query):
    locs = {
        "dubai": {"latitude": 25.2048, "longitude": 55.2708, "zone": "Dubai"},
        "abu dhabi": {"latitude": 24.4539, "longitude": 54.3773, "zone": "Abu Dhabi"},
        "sharjah": {"latitude": 25.3463, "longitude": 55.4209, "zone": "Sharjah"},
        "phoenix": {"latitude": 33.4484, "longitude": -112.0740, "zone": "Phoenix"},
        "doha": {"latitude": 25.2854, "longitude": 51.5310, "zone": "Doha"},
        "riyadh": {"latitude": 24.7136, "longitude": 46.6753, "zone": "Riyadh"},
    }
    for city, loc in locs.items():
        if city in query.lower():
            return loc
    return st.session_state.last_location


@st.cache_data(ttl=300, show_spinner=False)
def fetch_zone_heat_data(lat: float, lng: float, zone: str) -> dict:
    """Fetch real heat data from FortyGuard API for a zone. Cached 5 min."""
    if not FORTYGUARD_API_KEY:
        return {"error": "No API key", "zone": zone}
    try:
        from api.fortyguard import FortyGuardClient
        from utils.validation import flatten_location_data

        client = FortyGuardClient()
        today = datetime.now().strftime("%Y-%m-%d")
        activity_id = client.create_env_params(
            latitude=lat,
            longitude=lng,
            temperature=35.0,
            start_date=today,
            start_time="14:00",
            filter_type=1,
        )
        if not activity_id:
            return {"error": "API request failed", "zone": zone}
        result = client.wait_for_result(activity_id, timeout=60, poll_interval=3)
        flat = flatten_location_data(result)
        return {
            "zone": zone,
            "heat_index": flat.get("heat_index_celsius"),
            "humidity": flat.get("relative_humidity_percent"),
            "aqi": flat.get("air_quality:idx"),
            "apparent_temp": flat.get("apparent_temperature_celsius"),
            "status": "ok",
        }
    except Exception as e:
        return {"error": str(e), "zone": zone}


def fetch_all_zones() -> list[dict]:
    """Fetch heat data for all monitored zones."""
    zones = [
        {"name": "Dubai Downtown", "lat": 25.2048, "lng": 55.2708},
        {"name": "Abu Dhabi Central", "lat": 24.4539, "lng": 54.3773},
        {"name": "Sharjah City", "lat": 25.3463, "lng": 55.4209},
        {"name": "Phoenix, AZ", "lat": 33.4484, "lng": -112.0740},
    ]
    results = []
    for z in zones:
        data = fetch_zone_heat_data(z["lat"], z["lng"], z["name"])
        hi = data.get("heat_index")
        if hi is not None:
            is_alert = hi >= HEAT_INDEX_THRESHOLD
            status = "alert" if is_alert else "active"
        else:
            status = "unknown"
        results.append({**z, **data, "status": status})
    return results


def check_backend_health():
    try:
        import urllib.request

        req = urllib.request.Request("http://localhost:8501/_stcore/health", method="GET")
        urllib.request.urlopen(req, timeout=5)
        return True, "Backend running", "healthy"
    except Exception:
        return False, "Backend unreachable", "unhealthy"


def render_live_api_metrics():
    st.markdown(f'<div class="section-header">{svg("sparkles")} Live API Metrics</div>', unsafe_allow_html=True)
    ok, msg, cls = check_backend_health()
    ic = C["green"] if ok else C["red"]
    i = svg("check") if ok else svg("alert")
    st.markdown(
        f'<div style="background:{ic}10;border:1px solid {ic}40;border-radius:8px;padding:10px;margin-bottom:16px;display:flex;align-items:center;gap:8px;"><span style="color:{ic};">{i}</span><span style="color:{ic};font-weight:600;font-size:0.9rem;">{msg}</span></div>',
        unsafe_allow_html=True,
    )
    am = [m for m in st.session_state.messages if m.get("role") == "assistant"]
    if am:
        a1, a2 = st.columns(2)
        with a1:
            rt = [m.get("response_time_ms", 0) for m in am if m.get("response_time_ms")]
            avg = sum(rt) / len(rt) if rt else 0
            mc = C["green"] if avg < 500 else C["yellow"] if avg < 2000 else C["red"]
            st.markdown(
                f'<div class="metric-card" style="border-left:3px solid {mc};"><div class="metric-value" style="color:{mc};font-size:1.6rem;">{avg:.0f}ms</div><div class="metric-label">Avg Response Time</div></div>',
                unsafe_allow_html=True,
            )
        with a2:
            ss = [m["sentiment_score"] for m in am if m.get("sentiment_score") is not None]
            avg_s = sum(ss) / len(ss) if ss else 0
            if avg_s > 0.2:
                emoji, lbl, mc = "😊", "Positive", C["green"]
            elif avg_s < -0.2:
                emoji, lbl, mc = "😠", "Negative", C["red"]
            else:
                emoji, lbl, mc = "😐", "Neutral", C["text_muted"]
            st.markdown(
                f'<div class="metric-card" style="border-left:3px solid {mc};"><div class="metric-value" style="color:{mc};font-size:1.6rem;">{emoji} {avg_s:.2f}</div><div class="metric-label">{lbl} Sentiment</div></div>',
                unsafe_allow_html=True,
            )
        a3, a4 = st.columns(2)
        with a3:
            cs = [m["complexity_score"] for m in am if m.get("complexity_score") is not None]
            avg_c = sum(cs) / len(cs) if cs else 0
            if avg_c > 0.8:
                lbl, mc = "Complex", C["red"]
            elif avg_c > 0.3:
                lbl, mc = "Moderate", C["orange"]
            else:
                lbl, mc = "Simple", C["green"]
            st.markdown(
                f'<div class="metric-card" style="border-left:3px solid {mc};"><div class="metric-value" style="color:{mc};font-size:1.6rem;">{avg_c:.0%}</div><div class="metric-label">{lbl} Queries</div></div>',
                unsafe_allow_html=True,
            )
        with a4:
            ec = len([m for m in st.session_state.messages if m.get("escalated")])
            mc = C["red"] if ec > 0 else C["green"]
            lbl = f"{ec} Active" if ec else "All Clear"
            st.markdown(
                f'<div class="metric-card" style="border-left:3px solid {mc};"><div class="metric-value" style="color:{mc};font-size:1.6rem;">{ec}</div><div class="metric-label">{lbl}</div></div>',
                unsafe_allow_html=True,
            )
    if st.session_state.messages:
        with st.expander("View Full Metrics JSON"):
            metrics = generate_metrics_export()
            st.json(metrics)


def main():
    init_session()
    with st.sidebar:
        st.markdown(
            f"""<div style="text-align:center;margin-bottom:20px;padding:16px 0;background:linear-gradient(180deg,{C["surface"]} 0%,{C["bg"]} 100%);border-radius:12px;">
            <div style="display:flex;justify-content:center;align-items:center;gap:8px;margin-bottom:6px;">
                <span style="color:{C["red"]};font-size:1.6rem;filter:drop-shadow(0 0 6px {C["red"]}60);">🔥</span>
                <span style="font-size:1.6rem;font-weight:800;color:{C["text"]};letter-spacing:-0.5px;">HeatMind</span>
            </div>
            <div style="font-size:0.88rem;color:{C["text_muted"]};font-weight:600;">Heat Intelligence System</div>
            <div style="margin-top:8px;display:flex;justify-content:center;gap:6px;">
                <span style="padding:3px 8px;background:{C["green_dim"]}20;border:1px solid {C["green"]}30;border-radius:4px;font-size:0.75rem;font-weight:700;color:{C["green"]};">LIVE</span>
                <span style="padding:3px 8px;background:{C["border_light"]};border:1px solid {C["border"]};border-radius:4px;font-size:0.75rem;font-weight:700;color:{C["text_muted"]};">v1.0</span>
            </div>
        </div>""",
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="session-id" style="text-align:center;">{svg("database")} Session: {st.session_state.session_id[:8]}</div>',
            unsafe_allow_html=True,
        )
        st.divider()
        st.markdown(
            f'<div class="section-header" style="font-size:1rem;">{svg("map")} Location Settings</div>',
            unsafe_allow_html=True,
        )
        if st.session_state.last_location:
            st.markdown(
                f'<div class="zone-card"><div class="zone-name">{st.session_state.last_location["zone"]}</div><div class="zone-coords">{st.session_state.last_location["latitude"]:.4f}, {st.session_state.last_location["longitude"]:.4f}</div></div>',
                unsafe_allow_html=True,
            )
        else:
            st.info("No location set yet")
        st.divider()
        st.markdown(
            f'<div class="section-header" style="font-size:1rem;">{svg("activity")} Quick Stats</div>',
            unsafe_allow_html=True,
        )
        qs = st.session_state.query_count
        ms = len(st.session_state.messages)
        al = st.session_state.alert_count
        es = st.session_state.escalation_count
        st.markdown(
            f"""<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
        <div class="metric-card" style="padding:14px 8px;"><div class="metric-value" style="color:{C["accent"]};font-size:1.8rem;">{qs}</div><div class="metric-label" style="font-size:0.85rem;">Queries</div></div>
        <div class="metric-card" style="padding:14px 8px;"><div class="metric-value" style="color:{C["cyan"]};font-size:1.8rem;">{ms}</div><div class="metric-label" style="font-size:0.85rem;">Messages</div></div>
        <div class="metric-card" style="padding:14px 8px;"><div class="metric-value" style="color:{C["red"]};font-size:1.8rem;">{al}</div><div class="metric-label" style="font-size:0.85rem;">Alerts</div></div>
        <div class="metric-card" style="padding:14px 8px;"><div class="metric-value" style="color:{C["orange"]};font-size:1.8rem;">{es}</div><div class="metric-label" style="font-size:0.85rem;">Escalations</div></div>
        </div>""",
            unsafe_allow_html=True,
        )
        st.divider()
        st.markdown(
            f'<div class="section-header" style="font-size:1rem;">{svg("zap")} Actions</div>', unsafe_allow_html=True
        )
        bc1, bc2 = st.columns(2)
        with bc1:
            if st.button("New Session", use_container_width=True):
                memory = SessionMemory()
                st.session_state.session_id = memory.create_session("streamlit_user")
                st.session_state.memory = memory
                st.session_state.messages = []
                st.session_state.query_count = 0
                st.session_state.alert_count = 0
                st.session_state.total_response_time_ms = 0.0
                st.session_state.agent_counts = {"quick": 0, "deep": 0, "emergency": 0}
                st.rerun()
        with bc2:
            if st.button("Clear Chat", use_container_width=True):
                st.session_state.messages = []
                st.rerun()
        if st.session_state.messages:
            # Filter sensitive fields from exported messages
            safe_messages = []
            for msg in st.session_state.messages:
                safe_msg = {
                    "role": msg.get("role"),
                    "content": msg.get("content", "")[:500],
                    "agent": msg.get("agent"),
                    "timestamp": msg.get("timestamp"),
                }
                if msg.get("role") == "assistant":
                    safe_msg["response_time_ms"] = msg.get("response_time_ms")
                safe_messages.append(safe_msg)
            export_data = {
                "session_id": st.session_state.session_id,
                "location": {
                    "zone": st.session_state.last_location.get("zone"),
                    "latitude": st.session_state.last_location.get("latitude"),
                    "longitude": st.session_state.last_location.get("longitude"),
                },
                "queries": st.session_state.query_count,
                "messages": safe_messages,
                "exported_at": datetime.now(UTC).isoformat(),
            }
            st.download_button(
                label="Export Session JSON",
                data=json.dumps(export_data, indent=2),
                file_name=f"heatmind_{st.session_state.session_id[:8]}.json",
                mime="application/json",
                use_container_width=True,
                key="export_session",
            )
        st.divider()
        st.markdown(
            f'<div class="section-header" style="font-size:1rem;">{svg("wifi")} Connection</div>',
            unsafe_allow_html=True,
        )
        api_ok = bool(FORTYGUARD_API_KEY)
        if api_ok:
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:6px;color:{C["green"]};font-size:0.9rem;font-weight:700;">{svg("check")} FortyGuard API Connected</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:6px;color:{C["yellow"]};font-size:0.9rem;font-weight:700;">{svg("alert")} Demo Mode — No API Key</div>',
                unsafe_allow_html=True,
            )
        with st.expander("Backend Health"):
            ok, msg, cls = check_backend_health()
            ic = C["green"] if ok else C["red"]
            i = svg("check") if ok else svg("alert")
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:6px;color:{ic};font-weight:600;">{i} {msg}</div>',
                unsafe_allow_html=True,
            )
            if not ok and st.button("Retry", key="retry_health"):
                st.rerun()
        with st.expander("Export Metrics JSON"):
            if st.button("Download Metrics JSON", key="dl_metrics", use_container_width=True):
                m = generate_metrics_export()
                st.json(m)

    render_hero()
    tab_chat, tab_dashboard, tab_history, tab_monitor = st.tabs(["Chat", "Dashboard", "History", "Monitor"])

    with tab_chat:
        render_escalation_panel()
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg["role"] == "assistant":
                    render_msg_metadata(msg)

        if prompt := st.chat_input("Ask about heat conditions..."):
            user_msg = {"role": "user", "content": prompt}
            st.session_state.messages.append(user_msg)
            with st.chat_message("user"):
                st.markdown(prompt)
            st.session_state.last_location = parse_location_from_query(prompt)
            st.session_state.query_count += 1
            status_area = st.empty()
            escalate = (
                "escalat" in prompt.lower()
                or "urgent" in prompt.lower()
                or "emergency" in prompt.lower()
                or "hazard" in prompt.lower()
                or "danger" in prompt.lower()
            )
            if escalate:
                with status_area.container():
                    render_processing_status("classifying")
                    st.caption("🔍 Classifying query type...")
                with status_area.container():
                    render_processing_status("routing")
                    st.caption("🎯 Routing to optimal agent...")
                with status_area.container():
                    render_processing_status("analyzing")
                    st.caption("🧠 Analyzing heat data...")
                with status_area.container():
                    render_processing_status("processing")
                    st.caption("⚡ Processing with AI model...")
                with status_area.container():
                    render_processing_status("sentiment")
                    st.caption("💬 Analyzing response...")
                with status_area.container():
                    render_processing_status("escalating")
                    st.caption("🚨 Escalating to human agent...")
                with status_area.container():
                    render_processing_status("complete")
                    st.caption("✅ Response ready")
                status_area.empty()
                result = handle_query(prompt)
                result["agent"] = "emergency"
                result["escalated"] = True
                result["escalation_reason"] = "Critical heat hazard — immediate assistance required"
                result["ticket_id"] = f"ESCAL-{uuid.uuid4().hex[:8].upper()}"
                st.session_state.escalation_count += 1
            else:
                cycling_processing(status_area)
                result = handle_query(prompt)
                status_area.empty()
            agent = result.get("agent", "unknown")
            st.session_state.agent_counts[agent] = st.session_state.agent_counts.get(agent, 0) + 1
            st.session_state.total_response_time_ms += result.get("response_time_ms", 0)
            if agent == "emergency":
                st.session_state.alert_count += 1
            assistant_msg = {
                "role": "assistant",
                "content": result["response"],
                "agent": agent,
                "response_time_ms": result.get("response_time_ms"),
                "complexity_score": result.get("complexity_score"),
                "sentiment_score": result.get("sentiment_score"),
                "escalated": result.get("escalated", False),
                "escalation_reason": result.get("escalation_reason", ""),
                "ticket_id": result.get("ticket_id", ""),
                "timestamp": datetime.now(UTC).isoformat(),
            }
            st.session_state.messages.append(assistant_msg)
            if result.get("escalated"):
                display_escalation_banner(result["escalation_reason"], result["ticket_id"])
            with st.chat_message("assistant"):
                st.markdown(result["response"])
                render_msg_metadata(assistant_msg)

    with tab_dashboard:
        st.markdown(
            f'<div class="section-header">{svg("monitor")} Heat Intelligence Dashboard</div>', unsafe_allow_html=True
        )
        avg = (
            (st.session_state.total_response_time_ms / st.session_state.query_count)
            if st.session_state.query_count
            else 0
        )
        mc1, mc2, mc3, mc4 = st.columns(4)
        with mc1:
            st.markdown(
                f"""<div class="metric-card" style="border-top:3px solid {C["accent"]};">
                <div style="font-size:0.78rem;color:{C["text_dim"]};font-weight:700;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px;">{svg("search")} Queries</div>
                <div class="metric-value" style="color:{C["accent"]};font-size:2.2rem;">{st.session_state.query_count}</div>
                <div class="metric-label">Total Queries</div>
            </div>""",
                unsafe_allow_html=True,
            )
        with mc2:
            st.markdown(
                f"""<div class="metric-card" style="border-top:3px solid {C["red"]};">
                <div style="font-size:0.78rem;color:{C["text_dim"]};font-weight:700;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px;">{svg("alert")} Alerts</div>
                <div class="metric-value" style="color:{C["red"]};font-size:2.2rem;">{st.session_state.alert_count}</div>
                <div class="metric-label">Alerts Triggered</div>
            </div>""",
                unsafe_allow_html=True,
            )
        with mc3:
            rc = C["green"] if avg < 500 else C["yellow"] if avg < 2000 else C["red"]
            st.markdown(
                f"""<div class="metric-card" style="border-top:3px solid {C["green"]};">
                <div style="font-size:0.78rem;color:{C["text_dim"]};font-weight:700;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px;">{svg("zap")} Speed</div>
                <div class="metric-value" style="color:{rc};font-size:2.2rem;">{avg:.0f}<span style="font-size:1rem;font-weight:600;">ms</span></div>
                <div class="metric-label">Avg Response</div>
            </div>""",
                unsafe_allow_html=True,
            )
        with mc4:
            st.markdown(
                f"""<div class="metric-card" style="border-top:3px solid {C["purple"]};">
                <div style="font-size:0.78rem;color:{C["text_dim"]};font-weight:700;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px;">{svg("shield")} Uptime</div>
                <div class="metric-value" style="color:{C["purple"]};font-size:2.2rem;">100<span style="font-size:1rem;font-weight:600;">%</span></div>
                <div class="metric-label">System Uptime</div>
            </div>""",
                unsafe_allow_html=True,
            )
        ca, cb = st.columns(2)
        with ca:
            st.markdown(f'<div class="section-header">{svg("layers")} Agent Distribution</div>', unsafe_allow_html=True)
            for at in ["quick", "deep", "emergency"]:
                count = st.session_state.agent_counts.get(at, 0)
                total = max(st.session_state.query_count, 1)
                pct = (count / total) * 100
                color = C["green"] if at == "quick" else C["purple"] if at == "deep" else C["red"]
                st.markdown(
                    f'<div style="margin:10px 0;"><div style="display:flex;justify-content:space-between;margin-bottom:6px;"><span style="font-size:1rem;font-weight:700;color:{C["text"]};">{at.title()}</span><span style="font-size:0.9rem;font-weight:600;color:{C["text_muted"]};">{count} ({pct:.0f}%)</span></div><div style="height:8px;background:{C["border_light"]};border-radius:4px;overflow:hidden;"><div style="height:100%;width:{pct}%;background:{color};border-radius:4px;transition:width 0.5s ease;"></div></div></div>',
                    unsafe_allow_html=True,
                )
        with cb:
            st.markdown(f'<div class="section-header">{svg("map")} Active Location</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="zone-card"><div class="zone-name">{st.session_state.last_location["zone"]}</div><div class="zone-coords">{st.session_state.last_location["latitude"]}, {st.session_state.last_location["longitude"]}</div></div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="section-header" style="margin-top:16px;">{svg("alert")} Thresholds</div>',
                unsafe_allow_html=True,
            )
            t1, t2 = st.columns(2)
            with t1:
                st.markdown(
                    f'<div class="zone-card"><div class="zone-name" style="color:{C["yellow"]};font-size:1.3rem;">{HEAT_THRESHOLD_C}°C</div><div class="zone-coords" style="font-size:0.95rem;">Heat Threshold</div></div>',
                    unsafe_allow_html=True,
                )
            with t2:
                st.markdown(
                    f'<div class="zone-card"><div class="zone-name" style="color:{C["red"]};font-size:1.3rem;">{HEAT_INDEX_THRESHOLD}</div><div class="zone-coords" style="font-size:0.95rem;">Heat Index</div></div>',
                    unsafe_allow_html=True,
                )
        if st.session_state.messages:
            st.markdown(f'<div class="section-header">{svg("clock")} Recent Activity</div>', unsafe_allow_html=True)
            for msg in st.session_state.messages[-5:]:
                role = "You" if msg["role"] == "user" else "Agent"
                icon = svg("chat") if msg["role"] == "user" else svg("brain")
                color = C["text_muted"] if msg["role"] == "user" else C["accent"]
                st.markdown(
                    f'<div class="timeline-item"><div style="display:flex;align-items:center;gap:8px;"><span style="color:{color};">{icon}</span><span style="font-weight:700;font-size:0.95rem;color:{C["text"]};">{role}</span></div><div class="timeline-content">{msg["content"][:120]}{"..." if len(msg["content"]) > 120 else ""}</div></div>',
                    unsafe_allow_html=True,
                )

    with tab_history:
        st.markdown(f'<div class="section-header">{svg("clock")} Session History</div>', unsafe_allow_html=True)
        if not st.session_state.messages:
            st.info("No messages yet. Start a conversation in the Chat tab.")
        else:
            for i, msg in enumerate(reversed(st.session_state.messages)):
                role = msg["role"]
                icon = svg("chat") if role == "user" else svg("brain")
                color = C["text_muted"] if role == "user" else C["accent"]
                with st.expander(
                    f"{'You' if role == 'user' else 'Agent'}: {msg['content'][:80]}...", expanded=(i == 0)
                ):
                    st.markdown(msg["content"])
                    if role == "assistant":
                        render_msg_metadata(msg)

    with tab_monitor:
        st.markdown(f'<div class="section-header">{svg("activity")} Autonomous Monitor</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div style="color:{C["text_muted"]};font-size:1rem;margin-bottom:16px;">Checking every <strong style="color:{C["text"]};font-weight:700;">{MONITOR_INTERVAL_MINUTES} minutes</strong> &middot; Thresholds: <strong style="color:{C["yellow"]};">{HEAT_THRESHOLD_C}°C</strong> / <strong style="color:{C["red"]};">HI {HEAT_INDEX_THRESHOLD}</strong></div>',
            unsafe_allow_html=True,
        )

        if st.button("Refresh Zone Data", key="refresh_zones", use_container_width=True):
            fetch_zone_heat_data.clear()
            st.rerun()

        with st.spinner("Fetching live heat data from FortyGuard API..."):
            zones = fetch_all_zones()

        zc_cols = st.columns(min(len(zones), 4))
        for col, z in zip(zc_cols, zones, strict=True):
            is_alert = z["status"] == "alert"
            is_unknown = z["status"] == "unknown"
            bc = C["red"] if is_alert else C["green"] if not is_unknown else C["text_dim"]
            sc = C["red"] if is_alert else C["green"] if not is_unknown else C["text_dim"]
            st_txt = "ALERT" if is_alert else "Active" if not is_unknown else "No Data"
            si = svg("alert") if is_alert else svg("check") if not is_unknown else svg("alert")
            hi = z.get("heat_index")
            hum = z.get("humidity")
            aqi = z.get("aqi")
            with col:
                hi_str = f"{hi:.0f}" if hi is not None else "—"
                hum_str = f"{hum:.0f}%" if hum is not None else "—"
                aqi_str = f"{aqi:.0f}" if aqi is not None else "—"
                st.markdown(
                    f"""<div class="zone-card" style="border-left:3px solid {bc};min-height:140px;">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px;">
                        <div>
                            <div class="zone-name">{z["name"]}</div>
                            <div class="zone-coords" style="font-size:0.78rem;">{z["lat"]:.4f}, {z["lng"]:.4f}</div>
                        </div>
                        <span style="display:inline-flex;align-items:center;gap:4px;padding:3px 8px;background:{sc}20;border:1px solid {sc}40;border-radius:6px;color:{sc};font-weight:700;font-size:0.78rem;">{si} {st_txt}</span>
                    </div>
                    <div style="display:flex;gap:14px;margin-top:8px;">
                        <div style="text-align:center;">
                            <div style="font-size:1.3rem;font-weight:800;color:{sc};font-family:'JetBrains Mono',monospace;">{hi_str}{"°C" if hi is not None else ""}</div>
                            <div style="font-size:0.7rem;color:{C["text_dim"]};font-weight:600;text-transform:uppercase;">Heat Index</div>
                        </div>
                        <div style="text-align:center;">
                            <div style="font-size:1.3rem;font-weight:800;color:{C["cyan"]};font-family:'JetBrains Mono',monospace;">{hum_str}</div>
                            <div style="font-size:0.7rem;color:{C["text_dim"]};font-weight:600;text-transform:uppercase;">Humidity</div>
                        </div>
                        <div style="text-align:center;">
                            <div style="font-size:1.3rem;font-weight:800;color:{C["purple"]};font-family:'JetBrains Mono',monospace;">{aqi_str}</div>
                            <div style="font-size:0.7rem;color:{C["text_dim"]};font-weight:600;text-transform:uppercase;">AQI</div>
                        </div>
                    </div>
                </div>""",
                    unsafe_allow_html=True,
                )

        st.markdown("")
        st.markdown(f'<div class="section-header">{svg("alert")} Alert Feed</div>', unsafe_allow_html=True)
        alert_zones = [z for z in zones if z["status"] == "alert"]
        if not alert_zones:
            st.markdown(
                f"""<div class="alert-card-clear">
                <div style="display:flex;align-items:center;gap:8px;font-weight:700;font-size:1.1rem;">{svg("check")} All Clear</div>
                <div style="margin-top:8px;opacity:0.9;font-size:0.9rem;">Monitoring {len(zones)} zones. All within normal parameters.</div>
                <div style="margin-top:8px;display:flex;gap:12px;font-size:0.82rem;opacity:0.8;">
                    <span>Last check: {datetime.now(UTC).strftime("%H:%M UTC")}</span>
                    <span>&middot;</span>
                    <span>Next check: {MONITOR_INTERVAL_MINUTES}min</span>
                </div>
            </div>""",
                unsafe_allow_html=True,
            )
        else:
            for z in alert_zones:
                hi = z.get("heat_index")
                hi_str = f"{hi:.0f}°C" if hi is not None else "N/A"
                st.markdown(
                    f"""<div class="alert-card" style="margin-bottom:8px;">
                    <div style="display:flex;align-items:center;justify-content:space-between;">
                        <div style="display:flex;align-items:center;gap:8px;font-weight:700;font-size:1.05rem;">{svg("alert")} {z["name"]} — HI {hi_str}</div>
                        <span style="padding:3px 8px;background:rgba(255,255,255,0.2);border-radius:6px;font-size:0.78rem;font-weight:700;">CRITICAL</span>
                    </div>
                    <div style="margin-top:8px;opacity:0.9;font-size:0.88rem;">Heat index exceeds threshold ({HEAT_INDEX_THRESHOLD}). Immediate action required.</div>
                    <div style="margin-top:8px;display:flex;gap:6px;flex-wrap:wrap;">
                        <span style="padding:3px 8px;background:rgba(255,255,255,0.15);border-radius:4px;font-size:0.78rem;">Evacuate outdoor workers</span>
                        <span style="padding:3px 8px;background:rgba(255,255,255,0.15);border-radius:4px;font-size:0.78rem;">Open cooling centers</span>
                        <span style="padding:3px 8px;background:rgba(255,255,255,0.15);border-radius:4px;font-size:0.78rem;">Issue public warning</span>
                    </div>
                </div>""",
                    unsafe_allow_html=True,
                )


    # ── Footer ──
    st.markdown("")
    st.markdown(
        f"""<div style="text-align:center;padding:24px 0 8px 0;border-top:1px solid {C["border"]};margin-top:32px;">
        <div style="display:flex;justify-content:center;align-items:center;gap:8px;margin-bottom:6px;">
            <span style="color:{C["red"]};font-size:1rem;">🔥</span>
            <span style="font-size:1rem;font-weight:800;color:{C["text"]};letter-spacing:-0.3px;">HeatMind</span>
        </div>
        <div style="color:{C["text_dim"]};font-size:0.82rem;font-weight:500;">
            Multi-Agent Heat Intelligence System &middot; Built for FortyGuard Hackathon'26
        </div>
        <div style="margin-top:6px;color:{C["text_dim"]};font-size:0.78rem;">
            Built for FortyGuard Hackathon'26
        </div>
    </div>""",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
