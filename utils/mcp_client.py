"""
HeatMind MCP Client — Exposes HeatMind agents as MCP (Model Context Protocol) tools.

This module allows external AI agents (Claude, GPT, Gemini) to use HeatMind's
heat intelligence capabilities as MCP tools.

Usage:
    # As MCP server
    python -m utils.mcp_client serve

    # As client connecting to external MCP servers
    from utils.mcp_client import HeatMindMCPClient
    client = HeatMindMCPClient()
    result = client.query("What's the heat index in Dubai?")
"""

import json
import logging
import os
import sys
import time
from dataclasses import dataclass

from agents.deep_agent import DeepAgent
from agents.emergency_agent import EmergencyAgent
from agents.quick_agent import QuickAgent
from agents.router import route_query
from config import FORTYGUARD_API_KEY
from memory.session import SessionMemory

logger = logging.getLogger(__name__)

MAX_REQUEST_BODY_SIZE = 1024 * 1024  # 1MB


@dataclass
class MCPTool:
    name: str
    description: str
    input_schema: dict


HEATMIND_TOOLS = [
    MCPTool(
        name="query_heat_conditions",
        description="Get current heat conditions for a location (heat index, humidity, AQI)",
        input_schema={
            "type": "object",
            "properties": {
                "latitude": {"type": "number", "description": "Latitude coordinate"},
                "longitude": {"type": "number", "description": "Longitude coordinate"},
                "date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
                "zone": {"type": "string", "description": "Zone name for tracking"},
            },
            "required": ["latitude", "longitude", "date"],
        },
    ),
    MCPTool(
        name="deep_heat_analysis",
        description="Comprehensive heat risk assessment with heatmap, env params, and intelligence report",
        input_schema={
            "type": "object",
            "properties": {
                "latitude": {"type": "number", "description": "Latitude coordinate"},
                "longitude": {"type": "number", "description": "Longitude coordinate"},
                "date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
                "zone": {"type": "string", "description": "Zone name for tracking"},
                "polygon_aoi": {
                    "type": "object",
                    "description": "Polygon area of interest for heatmap",
                },
            },
            "required": ["latitude", "longitude", "date"],
        },
    ),
    MCPTool(
        name="emergency_heat_check",
        description="Check for emergency heat conditions and trigger alerts if threshold exceeded",
        input_schema={
            "type": "object",
            "properties": {
                "latitude": {"type": "number", "description": "Latitude coordinate"},
                "longitude": {"type": "number", "description": "Longitude coordinate"},
                "date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
                "zone": {"type": "string", "description": "Zone name for tracking"},
                "temperature": {"type": "number", "description": "Known temperature (if any)"},
            },
            "required": ["latitude", "longitude", "date"],
        },
    ),
    MCPTool(
        name="route_query",
        description="Classify a natural language query and return routing decision",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural language query about heat"},
            },
            "required": ["query"],
        },
    ),
    MCPTool(
        name="get_session_history",
        description="Retrieve conversation history for a session",
        input_schema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session ID"},
            },
            "required": ["session_id"],
        },
    ),
]


def _validate_mcp_tool_args(tool_name: str, args: dict) -> str | None:
    """Validate MCP tool arguments. Returns error message or None."""
    required = {
        "query_heat_conditions": ["latitude", "longitude", "date"],
        "deep_heat_analysis": ["latitude", "longitude", "date"],
        "emergency_heat_check": ["latitude", "longitude", "date"],
        "route_query": ["query"],
        "get_session_history": ["session_id"],
    }
    for field in required.get(tool_name, []):
        if field not in args or args[field] is None:
            return f"Missing required argument: {field}"

    if tool_name in ("query_heat_conditions", "deep_heat_analysis", "emergency_heat_check"):
        lat = args.get("latitude")
        lon = args.get("longitude")
        if not isinstance(lat, (int, float)) or not (-90 <= lat <= 90):
            return f"Invalid latitude: {lat}"
        if not isinstance(lon, (int, float)) or not (-180 <= lon <= 180):
            return f"Invalid longitude: {lon}"
    return None


class HeatMindMCPClient:
    """MCP client for HeatMind heat intelligence system."""

    def __init__(self):
        self.memory = SessionMemory()
        self.quick_agent = QuickAgent(memory=self.memory)
        self.deep_agent = DeepAgent(memory=self.memory)
        self.emergency_agent = EmergencyAgent(memory=self.memory)

    def list_tools(self) -> list:
        """List available MCP tools."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.input_schema,
            }
            for tool in HEATMIND_TOOLS
        ]

    def call_tool(self, tool_name: str, arguments: dict) -> dict:
        """Execute an MCP tool."""
        validation_error = _validate_mcp_tool_args(tool_name, arguments)
        if validation_error:
            return {"error": validation_error}

        if tool_name == "query_heat_conditions":
            return self._query_heat_conditions(arguments)
        elif tool_name == "deep_heat_analysis":
            return self._deep_heat_analysis(arguments)
        elif tool_name == "emergency_heat_check":
            return self._emergency_heat_check(arguments)
        elif tool_name == "route_query":
            return self._route_query(arguments)
        elif tool_name == "get_session_history":
            return self._get_session_history(arguments)
        else:
            return {"error": f"Unknown tool: {tool_name}"}

    def _query_heat_conditions(self, args: dict) -> dict:
        """Quick heat query."""
        if not FORTYGUARD_API_KEY:
            return {"error": "API key not configured"}

        session_id = self.memory.create_session("mcp_client")
        params = {
            "latitude": args["latitude"],
            "longitude": args["longitude"],
            "date": args["date"],
            "zone": args.get("zone", "unknown"),
        }
        result = self.quick_agent.handle(f"Get heat conditions for {params['zone']}", session_id, params)
        return {
            "tool": "query_heat_conditions",
            "result": result,
            "session_id": session_id,
        }

    def _deep_heat_analysis(self, args: dict) -> dict:
        """Deep heat analysis."""
        if not FORTYGUARD_API_KEY:
            return {"error": "API key not configured"}

        session_id = self.memory.create_session("mcp_client")
        params = {
            "latitude": args["latitude"],
            "longitude": args["longitude"],
            "date": args["date"],
            "zone": args.get("zone", "unknown"),
            "polygon_aoi": args.get("polygon_aoi"),
        }
        result = self.deep_agent.handle(f"Deep analysis for {params['zone']}", session_id, params)
        return {
            "tool": "deep_heat_analysis",
            "result": result,
            "session_id": session_id,
        }

    def _emergency_heat_check(self, args: dict) -> dict:
        """Emergency heat check."""
        if not FORTYGUARD_API_KEY:
            return {"error": "API key not configured"}

        session_id = self.memory.create_session("mcp_client")
        params = {
            "latitude": args["latitude"],
            "longitude": args["longitude"],
            "date": args["date"],
            "zone": args.get("zone", "unknown"),
            "temperature": args.get("temperature", 0),
        }
        result = self.emergency_agent.handle(f"Emergency check for {params['zone']}", session_id, params)
        return {
            "tool": "emergency_heat_check",
            "result": result,
            "session_id": session_id,
        }

    def _route_query(self, args: dict) -> dict:
        """Route a natural language query."""
        decision = route_query(args["query"])
        return {
            "tool": "route_query",
            "complexity": decision.complexity.value,
            "urgency": decision.urgency.value,
            "agent": decision.agent,
            "recommended_model": decision.recommended_model,
            "confidence": decision.confidence,
            "reasoning": decision.reasoning,
        }

    def _get_session_history(self, args: dict) -> dict:
        """Get session conversation history."""
        messages = self.memory.get_messages(args["session_id"])
        return {
            "tool": "get_session_history",
            "session_id": args["session_id"],
            "messages": messages,
            "count": len(messages),
        }

    def query(self, natural_query: str) -> dict:
        """High-level query interface — routes and executes automatically."""
        decision = route_query(natural_query)

        if decision.agent == "quick":
            agent = self.quick_agent
        elif decision.agent == "deep":
            agent = self.deep_agent
        elif decision.agent == "emergency":
            agent = self.emergency_agent
        else:
            return {"error": "Unknown agent type"}

        session_id = self.memory.create_session("mcp_query")
        params = {
            "latitude": 25.2048,
            "longitude": 55.2708,
            "date": "2026-08-17",
            "zone": "default",
        }

        result = agent.handle(natural_query, session_id, params)
        return {
            "query": natural_query,
            "routing": {
                "complexity": decision.complexity.value,
                "urgency": decision.urgency.value,
                "agent": decision.agent,
                "confidence": decision.confidence,
            },
            "result": result,
        }


def serve_mcp():
    """Run HeatMind as an MCP server (stdio transport)."""
    client = HeatMindMCPClient()

    mcp_secret = os.getenv("MCP_SECRET", "")
    if not mcp_secret:
        print("WARNING: MCP_SECRET not set. MCP server will accept any request.", file=sys.stderr)

    request_timestamps: list[float] = []
    RATE_LIMIT = 60
    RATE_WINDOW = 60.0

    print("HeatMind MCP Server started", file=sys.stderr)
    print("Listening on stdin...", file=sys.stderr)

    for line in sys.stdin:
        try:
            if len(line) > MAX_REQUEST_BODY_SIZE:
                logger.warning("Request body exceeds size limit (%d bytes)", MAX_REQUEST_BODY_SIZE)
                continue

            request = json.loads(line.strip())

            if mcp_secret:
                token = request.get("params", {}).get("token") or request.get("token", "")
                if token != mcp_secret:
                    logger.warning("MCP auth failed: invalid token")
                    response = {
                        "jsonrpc": "2.0",
                        "id": request.get("id"),
                        "error": {"code": -32000, "message": "Unauthorized: invalid MCP_SECRET"},
                    }
                    print(json.dumps(response))
                    sys.stdout.flush()
                    continue

            method = request.get("method")
            params = request.get("params", {})
            request_id = request.get("id")

            now = time.time()
            request_timestamps.append(now)
            request_timestamps[:] = [t for t in request_timestamps if now - t < RATE_WINDOW]
            if len(request_timestamps) > RATE_LIMIT:
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32000, "message": "Rate limit exceeded. Max 60 requests per minute."},
                }
                print(json.dumps(response))
                sys.stdout.flush()
                continue

            if method == "initialize":
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "serverInfo": {
                            "name": "heatmind",
                            "version": "1.0.0",
                        },
                    },
                }
            elif method == "tools/list":
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"tools": client.list_tools()},
                }
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                result = client.call_tool(tool_name, arguments)
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]},
                }
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32601, "message": f"Unknown method: {method}"},
                }

            print(json.dumps(response))
            sys.stdout.flush()

        except json.JSONDecodeError:
            continue
        except Exception:
            logger.error("MCP server internal error", exc_info=True)
            error_response = {
                "jsonrpc": "2.0",
                "id": request_id if "request_id" in locals() else None,
                "error": {"code": -32603, "message": "Internal error"},
            }
            print(json.dumps(error_response))
            sys.stdout.flush()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        serve_mcp()
    else:
        client = HeatMindMCPClient()
        print("HeatMind MCP Client")
        print("Available tools:")
        for tool in client.list_tools():
            print(f"  - {tool['name']}: {tool['description']}")
