"""Tests for MCP Client — tool listing, validation, dispatch, auth."""

from unittest.mock import patch

import pytest

from utils.mcp_client import HeatMindMCPClient, MCPTool, _validate_mcp_tool_args


class TestMCPTool:
    def test_dataclass_fields(self):
        tool = MCPTool(name="test", description="desc", input_schema={"type": "object"})
        assert tool.name == "test"
        assert tool.description == "desc"
        assert tool.input_schema["type"] == "object"


class TestValidateMcpToolArgs:
    def test_valid_query_heat_conditions(self):
        result = _validate_mcp_tool_args(
            "query_heat_conditions",
            {"latitude": 25.0, "longitude": 55.0, "date": "2026-08-15"},
        )
        assert result is None

    def test_missing_latitude(self):
        result = _validate_mcp_tool_args(
            "query_heat_conditions",
            {"longitude": 55.0, "date": "2026-08-15"},
        )
        assert "latitude" in result

    def test_missing_longitude(self):
        result = _validate_mcp_tool_args(
            "query_heat_conditions",
            {"latitude": 25.0, "date": "2026-08-15"},
        )
        assert "longitude" in result

    def test_missing_date(self):
        result = _validate_mcp_tool_args(
            "query_heat_conditions",
            {"latitude": 25.0, "longitude": 55.0},
        )
        assert "date" in result

    def test_invalid_latitude_out_of_range(self):
        result = _validate_mcp_tool_args(
            "query_heat_conditions",
            {"latitude": 999, "longitude": 55.0, "date": "2026-08-15"},
        )
        assert "latitude" in result

    def test_invalid_longitude_out_of_range(self):
        result = _validate_mcp_tool_args(
            "query_heat_conditions",
            {"latitude": 25.0, "longitude": 999, "date": "2026-08-15"},
        )
        assert "longitude" in result

    def test_valid_deep_heat_analysis(self):
        result = _validate_mcp_tool_args(
            "deep_heat_analysis",
            {"latitude": 25.0, "longitude": 55.0, "date": "2026-08-15"},
        )
        assert result is None

    def test_valid_route_query(self):
        result = _validate_mcp_tool_args("route_query", {"query": "how hot"})
        assert result is None

    def test_missing_query(self):
        result = _validate_mcp_tool_args("route_query", {})
        assert "query" in result

    def test_valid_session_history(self):
        result = _validate_mcp_tool_args("get_session_history", {"session_id": "abc-123"})
        assert result is None

    def test_missing_session_id(self):
        result = _validate_mcp_tool_args("get_session_history", {})
        assert "session_id" in result

    def test_unknown_tool(self):
        result = _validate_mcp_tool_args("nonexistent_tool", {})
        assert result is None

    def test_lat_none_value(self):
        result = _validate_mcp_tool_args(
            "query_heat_conditions",
            {"latitude": None, "longitude": 55.0, "date": "2026-08-15"},
        )
        assert "latitude" in result


class TestHeatMindMCPClient:
    @pytest.fixture
    def client(self):
        with patch("utils.mcp_client.SessionMemory") as mock_mem:
            with patch("utils.mcp_client.QuickAgent"):
                with patch("utils.mcp_client.DeepAgent"):
                    with patch("utils.mcp_client.EmergencyAgent"):
                        mem = mock_mem.return_value
                        mem.create_session.return_value = "test-session"
                        c = HeatMindMCPClient()
                        c.memory = mem
                        yield c

    def test_list_tools(self, client):
        tools = client.list_tools()
        assert len(tools) == 5
        names = [t["name"] for t in tools]
        assert "query_heat_conditions" in names
        assert "deep_heat_analysis" in names
        assert "emergency_heat_check" in names
        assert "route_query" in names
        assert "get_session_history" in names

    def test_list_tools_schema(self, client):
        tools = client.list_tools()
        for tool in tools:
            assert "inputSchema" in tool
            assert tool["inputSchema"]["type"] == "object"

    def test_call_tool_validation_error(self, client):
        result = client.call_tool("query_heat_conditions", {})
        assert "error" in result

    def test_call_tool_unknown_tool(self, client):
        result = client.call_tool("nonexistent", {})
        assert "error" in result
        assert "Unknown tool" in result["error"]

    def test_call_tool_route_query(self, client):
        result = client.call_tool("route_query", {"query": "how hot is it"})
        assert result["tool"] == "route_query"
        assert "complexity" in result
        assert "urgency" in result

    def test_call_tool_get_session_history(self, client):
        client.memory.get_messages.return_value = [{"role": "user", "content": "hello"}]
        result = client.call_tool("get_session_history", {"session_id": "test-session"})
        assert result["tool"] == "get_session_history"
        assert result["count"] == 1

    @patch("utils.mcp_client.FORTYGUARD_API_KEY", "")
    def test_query_heat_conditions_no_api_key(self, client):
        result = client.call_tool(
            "query_heat_conditions",
            {"latitude": 25.0, "longitude": 55.0, "date": "2026-08-15"},
        )
        assert "error" in result
        assert "API key" in result["error"]

    def test_call_tool_dispatches_correctly(self, client):
        with patch("utils.mcp_client.FORTYGUARD_API_KEY", "test-key"):
            client.quick_agent.handle.return_value = {"agent": "quick", "response": "ok"}
            result = client.call_tool(
                "query_heat_conditions",
                {"latitude": 25.0, "longitude": 55.0, "date": "2026-08-15"},
            )
            assert result["tool"] == "query_heat_conditions"
            client.quick_agent.handle.assert_called_once()

    def test_get_session_history_empty(self, client):
        client.memory.get_messages.return_value = []
        result = client.call_tool("get_session_history", {"session_id": "empty-session"})
        assert result["count"] == 0


class TestMCPModule:
    def test_max_request_body_size(self):
        from utils.mcp_client import MAX_REQUEST_BODY_SIZE

        assert MAX_REQUEST_BODY_SIZE == 1024 * 1024

    def test_heatmind_tools_count(self):
        from utils.mcp_client import HEATMIND_TOOLS

        assert len(HEATMIND_TOOLS) == 5
