"""Tests for utils/mcp_client.py — MCP client, tools, and server."""

from unittest.mock import patch

import pytest

from utils.mcp_client import (
    HEATMIND_TOOLS,
    HeatMindMCPClient,
    MCPTool,
    _validate_mcp_tool_args,
)


class TestMCPTool:
    def test_tool_dataclass(self):
        t = MCPTool(name="test", description="desc", input_schema={})
        assert t.name == "test"
        assert t.description == "desc"


class TestHeatmindTools:
    def test_tools_list_not_empty(self):
        assert len(HEATMIND_TOOLS) == 5

    def test_tool_names(self):
        names = [t.name for t in HEATMIND_TOOLS]
        assert "query_heat_conditions" in names
        assert "deep_heat_analysis" in names
        assert "emergency_heat_check" in names
        assert "route_query" in names
        assert "get_session_history" in names

    def test_all_tools_have_schemas(self):
        for tool in HEATMIND_TOOLS:
            assert "type" in tool.input_schema
            assert "properties" in tool.input_schema
            assert "required" in tool.input_schema


class TestValidateMcpToolArgs:
    def test_valid_query_heat(self):
        err = _validate_mcp_tool_args("query_heat_conditions", {"latitude": 33.5, "longitude": -112, "date": "2026-08-19"})
        assert err is None

    def test_valid_deep_analysis(self):
        err = _validate_mcp_tool_args("deep_heat_analysis", {"latitude": 33.5, "longitude": -112, "date": "2026-08-19"})
        assert err is None

    def test_valid_emergency(self):
        err = _validate_mcp_tool_args("emergency_heat_check", {"latitude": 33.5, "longitude": -112, "date": "2026-08-19"})
        assert err is None

    def test_valid_route_query(self):
        err = _validate_mcp_tool_args("route_query", {"query": "temperature in Miami"})
        assert err is None

    def test_valid_session_history(self):
        err = _validate_mcp_tool_args("get_session_history", {"session_id": "abc-123"})
        assert err is None

    def test_missing_latitude(self):
        err = _validate_mcp_tool_args("query_heat_conditions", {"longitude": -112, "date": "2026-08-19"})
        assert err is not None
        assert "latitude" in err

    def test_missing_longitude(self):
        err = _validate_mcp_tool_args("query_heat_conditions", {"latitude": 33.5, "date": "2026-08-19"})
        assert err is not None
        assert "longitude" in err

    def test_missing_date(self):
        err = _validate_mcp_tool_args("query_heat_conditions", {"latitude": 33.5, "longitude": -112})
        assert err is not None
        assert "date" in err

    def test_missing_query(self):
        err = _validate_mcp_tool_args("route_query", {})
        assert err is not None
        assert "query" in err

    def test_missing_session_id(self):
        err = _validate_mcp_tool_args("get_session_history", {})
        assert err is not None
        assert "session_id" in err

    def test_invalid_latitude_too_high(self):
        err = _validate_mcp_tool_args("query_heat_conditions", {"latitude": 91, "longitude": -112, "date": "2026-08-19"})
        assert err is not None
        assert "latitude" in err

    def test_invalid_latitude_negative(self):
        err = _validate_mcp_tool_args("query_heat_conditions", {"latitude": -91, "longitude": -112, "date": "2026-08-19"})
        assert err is not None

    def test_invalid_longitude_too_high(self):
        err = _validate_mcp_tool_args("query_heat_conditions", {"latitude": 33.5, "longitude": 181, "date": "2026-08-19"})
        assert err is not None

    def test_invalid_latitude_string(self):
        err = _validate_mcp_tool_args("query_heat_conditions", {"latitude": "abc", "longitude": -112, "date": "2026-08-19"})
        assert err is not None

    def test_null_latitude(self):
        err = _validate_mcp_tool_args("query_heat_conditions", {"latitude": None, "longitude": -112, "date": "2026-08-19"})
        assert err is not None

    def test_unknown_tool_passes(self):
        err = _validate_mcp_tool_args("nonexistent_tool", {})
        assert err is None

    def test_boundary_latitude(self):
        err = _validate_mcp_tool_args("query_heat_conditions", {"latitude": 90, "longitude": 180, "date": "2026-08-19"})
        assert err is None

    def test_boundary_longitude(self):
        err = _validate_mcp_tool_args("query_heat_conditions", {"latitude": -90, "longitude": -180, "date": "2026-08-19"})
        assert err is None


class TestHeatMindMCPClient:
    @pytest.fixture
    def client(self):
        with patch("utils.mcp_client.QuickAgent"), \
             patch("utils.mcp_client.DeepAgent"), \
             patch("utils.mcp_client.EmergencyAgent"):
            return HeatMindMCPClient()

    def test_list_tools(self, client):
        tools = client.list_tools()
        assert len(tools) == 5
        assert all("name" in t for t in tools)
        assert all("description" in t for t in tools)
        assert all("inputSchema" in t for t in tools)

    def test_call_tool_unknown(self, client):
        result = client.call_tool("nonexistent", {})
        assert "error" in result

    def test_call_tool_validation_error(self, client):
        result = client.call_tool("query_heat_conditions", {})
        assert "error" in result
        assert "Missing" in result["error"]

    def test_route_query(self, client):
        result = client.call_tool("route_query", {"query": "What's the temperature?"})
        assert result["tool"] == "route_query"
        assert "complexity" in result
        assert "urgency" in result
        assert "agent" in result

    def test_get_session_history_empty(self, client):
        result = client.call_tool("get_session_history", {"session_id": "nonexistent"})
        assert result["tool"] == "get_session_history"
        assert result["count"] == 0

    def test_query_no_api_key(self, client):
        with patch("utils.mcp_client.FORTYGUARD_API_KEY", ""):
            result = client.call_tool("query_heat_conditions", {"latitude": 33.5, "longitude": -112, "date": "2026-08-19"})
            assert "error" in result
            assert "API key" in result["error"]

    def test_deep_analysis_no_api_key(self, client):
        with patch("utils.mcp_client.FORTYGUARD_API_KEY", ""):
            result = client.call_tool("deep_heat_analysis", {"latitude": 33.5, "longitude": -112, "date": "2026-08-19"})
            assert "error" in result

    def test_emergency_no_api_key(self, client):
        with patch("utils.mcp_client.FORTYGUARD_API_KEY", ""):
            result = client.call_tool("emergency_heat_check", {"latitude": 33.5, "longitude": -112, "date": "2026-08-19"})
            assert "error" in result

    def test_high_level_query(self, client):
        with patch("utils.mcp_client.FORTYGUARD_API_KEY", ""):
            result = client.query("What's the temperature in Miami?")
            assert "routing" in result
            assert "result" in result
