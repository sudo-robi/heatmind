"""Agent spec loader — every HeatMind agent is defined by a markdown spec.

Agents self-describe through ``agents/specs/*.md`` files (YAML frontmatter +
markdown body), following the pattern of ``everything-claude-code/agents/*.md``.
At runtime an agent loads its own spec and the LLM reads it as its operating
manual, so role, tools, decision rules, and escalation policy are documents —
not code.
"""

import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

SPECS_DIR = Path(__file__).resolve().parent.parent / "agents" / "specs"

_default_spec = {
    "name": "coordinator",
    "description": "Generic HeatMind agent.",
    "tools": "env_params, heatmap, heat_intelligence, satellite, streetview",
    "model": "recommended",
    "autonomy": "full",
}


def load_spec(name: str) -> dict:
    """Load and parse an agent spec by name, falling back to the default."""
    spec = dict(_default_spec)
    path = SPECS_DIR / f"{name}.md"
    if not path.exists():
        logger.debug("No spec file for '%s'; using default", name)
        spec["body"] = f"You are the {name} sub-agent inside HeatMind. Coordinate heat-intelligence work autonomously."
        return spec
    return parse_spec(path.read_text(encoding="utf-8"))


def parse_spec(text: str) -> dict:
    """Parse a spec: YAML frontmatter between leading ``---`` markers + body."""
    spec = dict(_default_spec)
    text = text.lstrip("\ufeff").lstrip()
    if not text.startswith("---"):
        spec["body"] = text
        return spec
    parts = text.split("---", 2)
    if len(parts) < 3:
        spec["body"] = text
        return spec
    try:
        meta = yaml.safe_load(parts[1]) or {}
        if isinstance(meta, dict):
            spec.update(meta)
    except yaml.YAMLError as e:
        logger.warning("Failed to parse frontmatter in spec: %s", e)
    spec["body"] = parts[2].strip()
    return spec


def tool_list(spec: dict) -> list[str]:
    """Return the spec's allowed tools as a list."""
    tools = spec.get("tools") or ""
    if isinstance(tools, str):
        return [t.strip() for t in tools.split(",") if t.strip()]
    return list(tools)


def all_spec_names() -> list[str]:
    """Return the names of all spec files on disk."""
    if not SPECS_DIR.exists():
        return []
    return [p.stem for p in SPECS_DIR.glob("*.md")]


def render_spec(spec: dict) -> str:
    """Render a spec back to a compact markdown string for the LLM system prompt."""
    lines = [
        f"# Agent: {spec.get('name', 'coordinator')}",
        f"Description: {spec.get('description', '')}",
        f"Tools: {', '.join(tool_list(spec))}",
        f"Autonomy: {spec.get('autonomy', 'full')}",
        "",
        spec.get("body", ""),
    ]
    return "\n".join(lines)
