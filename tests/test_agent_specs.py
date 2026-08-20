"""Tests for the agent spec system (utils/agent_specs.py)."""

from utils.agent_specs import all_spec_names, load_spec, parse_spec, render_spec, tool_list


class TestParseSpec:
    def test_frontmatter_and_body(self):
        text = """---\nname: coordinator\ntools: env_params, heatmap\n---\n\nYou are the lead.\n"""
        spec = parse_spec(text)
        assert spec["name"] == "coordinator"
        assert spec["tools"] == "env_params, heatmap"
        assert "You are the lead." in spec["body"]

    def test_no_frontmatter_uses_default(self):
        spec = parse_spec("Just a body with no frontmatter.")
        assert spec["name"] == "coordinator"
        assert spec["body"] == "Just a body with no frontmatter."

    def test_defaults_applied_when_meta_sparse(self):
        spec = parse_spec("---\nname: analyst\n---\n\nBody here.")
        assert spec["name"] == "analyst"
        assert spec["tools"] == "env_params, heatmap, heat_intelligence, satellite, streetview"


class TestLoadSpec:
    def test_loads_existing_spec(self):
        spec = load_spec("coordinator")
        assert spec["name"] == "coordinator"
        assert "You are the HeatMind Lead Coordinator" in spec["body"]

    def test_missing_spec_falls_back_to_default(self):
        spec = load_spec("does-not-exist")
        assert spec["name"] == "coordinator"
        assert "body" in spec

    def test_emergency_and_alert_specs_exist(self):
        for name in ("emergency-coordinator", "public-alert", "heat-analyst"):
            spec = load_spec(name)
            assert spec["name"] == name
            assert spec["body"].strip()


class TestSpecHelpers:
    def test_tool_list(self):
        spec = parse_spec("---\ntools: env_params, heatmap\n---\n\n")
        assert tool_list(spec) == ["env_params", "heatmap"]

    def test_all_spec_names_finds_md_files(self):
        names = all_spec_names()
        assert "coordinator" in names
        assert "heat-analyst" in names
        assert "emergency-coordinator" in names
        assert "public-alert" in names

    def test_render_spec_contains_role(self):
        rendered = render_spec(load_spec("coordinator"))
        assert "# Agent: coordinator" in rendered
        assert "Tools:" in rendered
        assert "Autonomy:" in rendered
