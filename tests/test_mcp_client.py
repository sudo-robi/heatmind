"""Tests for MCP Client — tool listing, validation, dispatch, auth."""

import json
import os
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

    def test_call_tool_deep_heat_analysis_dispatches(self, client):
        with patch("utils.mcp_client.FORTYGUARD_API_KEY", "test-key"):
            client.deep_agent.handle.return_value = {"agent": "deep", "response": "ok"}
            result = client.call_tool(
                "deep_heat_analysis",
                {"latitude": 25.0, "longitude": 55.0, "date": "2026-08-15"},
            )
            assert result["tool"] == "deep_heat_analysis"
            client.deep_agent.handle.assert_called_once()

    def test_deep_heat_analysis_no_api_key(self, client):
        with patch("utils.mcp_client.FORTYGUARD_API_KEY", ""):
            result = client.call_tool(
                "deep_heat_analysis",
                {"latitude": 25.0, "longitude": 55.0, "date": "2026-08-15"},
            )
            assert "error" in result
            assert "API key" in result["error"]

    def test_call_tool_emergency_heat_check_dispatches(self, client):
        with patch("utils.mcp_client.FORTYGUARD_API_KEY", "test-key"):
            client.emergency_agent.handle.return_value = {"agent": "emergency", "response": "ok"}
            result = client.call_tool(
                "emergency_heat_check",
                {"latitude": 25.0, "longitude": 55.0, "date": "2026-08-15"},
            )
            assert result["tool"] == "emergency_heat_check"
            client.emergency_agent.handle.assert_called_once()

    def test_emergency_heat_check_no_api_key(self, client):
        with patch("utils.mcp_client.FORTYGUARD_API_KEY", ""):
            result = client.call_tool(
                "emergency_heat_check",
                {"latitude": 25.0, "longitude": 55.0, "date": "2026-08-15"},
            )
            assert "error" in result
            assert "API key" in result["error"]

    def test_high_level_query(self, client):
        client.quick_agent.handle.return_value = {"agent": "quick", "response": "ok"}
        result = client.query("What's the temperature in Dubai?")
        assert "routing" in result
        assert "result" in result

    def test_high_level_query_deep_agent(self, client):
        client.deep_agent.handle.return_value = {"agent": "deep", "response": "ok"}
        result = client.query("Give me a full heat risk analysis for Dubai with heatmap")
        assert "routing" in result
        assert "result" in result

    def test_high_level_query_emergency_agent(self, client):
        client.emergency_agent.handle.return_value = {"agent": "emergency", "response": "ok"}
        result = client.query("EMERGENCY: extreme heat alert for outdoor workers in Dubai right now!")
        assert "routing" in result
        assert "result" in result


class TestMCPModule:
    def test_max_request_body_size(self):
        from utils.mcp_client import MAX_REQUEST_BODY_SIZE

        assert MAX_REQUEST_BODY_SIZE == 1024 * 1024

    def test_heatmind_tools_count(self):
        from utils.mcp_client import HEATMIND_TOOLS

        assert len(HEATMIND_TOOLS) == 5


class TestServeMCP:
    def _run_serve(self, lines, env_overrides=None):
        from utils.mcp_client import serve_mcp

        env = env_overrides or {}
        with patch("utils.mcp_client.sys") as mock_sys:
            mock_sys.stdin = lines
            mock_sys.stderr = mock_sys.stderr
            with patch("builtins.print") as mock_print:
                with patch("utils.mcp_client.HeatMindMCPClient") as MockClient:
                    mock_client = MockClient.return_value
                    mock_client.list_tools.return_value = [
                        {"name": "t1", "description": "d", "inputSchema": {"type": "object"}}
                    ]
                    mock_client.call_tool.return_value = {"tool": "t1", "result": "ok"}
                    with patch.dict("os.environ", env, clear=False):
                        serve_mcp()
                    return mock_print

    def test_serve_mcp_initialize(self):
        request = json.dumps({"method": "initialize", "id": 1, "params": {}}) + "\n"
        mock_print = self._run_serve([request])
        output = mock_print.call_args_list[-1][0][0]
        resp = json.loads(output)
        assert resp["id"] == 1
        assert "result" in resp
        assert resp["result"]["protocolVersion"] == "2024-11-05"

    def test_serve_mcp_tools_list(self):
        request = json.dumps({"method": "tools/list", "id": 2, "params": {}}) + "\n"
        mock_print = self._run_serve([request])
        output = mock_print.call_args_list[-1][0][0]
        resp = json.loads(output)
        assert resp["id"] == 2
        assert "tools" in resp["result"]

    def test_serve_mcp_unknown_method(self):
        request = json.dumps({"method": "unknown/method", "id": 3, "params": {}}) + "\n"
        mock_print = self._run_serve([request])
        output = mock_print.call_args_list[-1][0][0]
        resp = json.loads(output)
        assert resp["id"] == 3
        assert "error" in resp
        assert resp["error"]["code"] == -32601

    def test_serve_mcp_json_decode_error(self):
        mock_print = self._run_serve(["not json\n"])
        json_calls = [c for c in mock_print.call_args_list if c[0] and c[0][0].startswith("{")]
        assert len(json_calls) == 0

    def test_serve_mcp_auth_failure(self):
        request = json.dumps({"method": "initialize", "id": 4, "params": {"token": "wrong"}}) + "\n"
        mock_print = self._run_serve([request], env_overrides={"MCP_SECRET": "real-secret"})
        json_calls = [c for c in mock_print.call_args_list if c[0] and c[0][0].startswith("{")]
        output = json_calls[-1][0][0]
        resp = json.loads(output)
        assert "error" in resp
        assert "Unauthorized" in resp["error"]["message"]

    def test_serve_mcp_auth_success(self):
        request = json.dumps({"method": "initialize", "id": 5, "params": {"token": "real-secret"}}) + "\n"
        mock_print = self._run_serve([request], env_overrides={"MCP_SECRET": "real-secret"})
        json_calls = [c for c in mock_print.call_args_list if c[0] and c[0][0].startswith("{")]
        output = json_calls[-1][0][0]
        resp = json.loads(output)
        assert "result" in resp

    def test_serve_mcp_request_too_large(self):
        huge = "x" * (1024 * 1024 + 1)
        mock_print = self._run_serve([huge + "\n"])
        json_calls = [c for c in mock_print.call_args_list if c[0] and c[0][0].startswith("{")]
        assert len(json_calls) == 0

    def test_serve_mcp_tools_call(self):
        request = (
            json.dumps(
                {
                    "method": "tools/call",
                    "id": 6,
                    "params": {"name": "route_query", "arguments": {"query": "how hot"}},
                }
            )
            + "\n"
        )
        mock_print = self._run_serve([request])
        json_calls = [c for c in mock_print.call_args_list if c[0] and c[0][0].startswith("{")]
        output = json_calls[-1][0][0]
        resp = json.loads(output)
        assert resp["id"] == 6
        assert "result" in resp
        assert "content" in resp["result"]

    def test_serve_mcp_exception_handling(self):
        from utils.mcp_client import serve_mcp

        request = json.dumps({"method": "tools/call", "id": 7, "params": {"name": "bad", "arguments": {}}}) + "\n"
        with patch("utils.mcp_client.sys") as mock_sys:
            mock_sys.stdin = [request]
            with patch("builtins.print") as mock_print:
                with patch("utils.mcp_client.HeatMindMCPClient") as MockClient:
                    mock_instance = MockClient.return_value
                    mock_instance.call_tool.side_effect = RuntimeError("boom")
                    serve_mcp()
                    json_calls = [c for c in mock_print.call_args_list if c[0] and c[0][0].startswith("{")]
                    output = json_calls[-1][0][0]
                    resp = json.loads(output)
                    assert resp["error"]["code"] == -32603

    def test_serve_mcp_no_mcp_secret_warning(self):
        from utils.mcp_client import serve_mcp

        request = json.dumps({"method": "initialize", "id": 8, "params": {}}) + "\n"
        with patch("utils.mcp_client.sys") as mock_sys:
            mock_sys.stdin = [request]
            mock_sys.stderr = mock_sys.stderr
            with patch("builtins.print") as mock_print:
                with patch("utils.mcp_client.HeatMindMCPClient"):
                    saved = os.environ.pop("MCP_SECRET", None)
                    try:
                        serve_mcp()
                    finally:
                        if saved is not None:
                            os.environ["MCP_SECRET"] = saved
                    all_output = str(mock_print.call_args_list)
                    assert "MCP_SECRET" in all_output

    def test_serve_mcp_rate_limit(self):
        requests = []
        for i in range(62):
            requests.append(json.dumps({"method": "initialize", "id": i, "params": {}}) + "\n")
        mock_print = self._run_serve(requests)
        all_output = str(mock_print.call_args_list)
        assert "Rate limit" in all_output

    def test_serve_mcp_no_mcp_secret_no_auth(self):
        request = json.dumps({"method": "initialize", "id": 9, "params": {}}) + "\n"
        from utils.mcp_client import serve_mcp

        with patch("utils.mcp_client.sys") as mock_sys:
            mock_sys.stdin = [request]
            with patch("builtins.print") as mock_print:
                with patch("utils.mcp_client.HeatMindMCPClient"):
                    os.environ.pop("MCP_SECRET", None)
                    serve_mcp()
                    json_calls = [c for c in mock_print.call_args_list if c[0] and c[0][0].startswith("{")]
                    output = json_calls[-1][0][0]
                    resp = json.loads(output)
                    assert "result" in resp

    def test_serve_mcp_auth_token_in_top_level(self):
        request = json.dumps({"method": "initialize", "id": 10, "token": "real-secret", "params": {}}) + "\n"
        mock_print = self._run_serve([request], env_overrides={"MCP_SECRET": "real-secret"})
        json_calls = [c for c in mock_print.call_args_list if c[0] and c[0][0].startswith("{")]
        output = json_calls[-1][0][0]
        resp = json.loads(output)
        assert "result" in resp

    def test_serve_mcp_auth_token_in_params(self):
        request = json.dumps({"method": "initialize", "id": 11, "params": {"token": "real-secret"}}) + "\n"
        mock_print = self._run_serve([request], env_overrides={"MCP_SECRET": "real-secret"})
        json_calls = [c for c in mock_print.call_args_list if c[0] and c[0][0].startswith("{")]
        output = json_calls[-1][0][0]
        resp = json.loads(output)
        assert "result" in resp
