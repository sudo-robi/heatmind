"""Tests for agent personas and system prompts (utils/personas.py)."""

from utils.personas import (
    TOOL_WHITELIST,
    build_answer_system_prompt,
    build_plan_system_prompt,
    build_tool_manifest,
    persona_for,
)


class TestPersonas:
    def test_whitelist_contains_five_endpoints(self):
        assert TOOL_WHITELIST == ("env_params", "heatmap", "heat_intelligence", "satellite", "streetview")

    def test_persona_for_known_agents(self):
        for agent in ("quick", "deep", "emergency"):
            assert persona_for(agent)

    def test_persona_for_unknown_falls_back(self):
        assert persona_for("llm")

    def test_tool_manifest_describes_tools(self):
        manifest = build_tool_manifest()
        for tool in TOOL_WHITELIST:
            assert tool in manifest

    def test_plan_prompt_has_phase_marker(self):
        prompt = build_plan_system_prompt("quick")
        assert "[PHASE: PLAN]" in prompt
        assert "tool_calls" in prompt

    def test_answer_prompt_has_phase_marker(self):
        prompt = build_answer_system_prompt("deep")
        assert "[PHASE: ANSWER]" in prompt
        assert "summary" in prompt
        assert "severity" in prompt
