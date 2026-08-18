from datetime import UTC, datetime
from uuid import uuid4

from pymongo import MongoClient

from config import MONGO_DB, MONGO_URI, _validate_mongo_uri

_client: MongoClient | None = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI)
    return _client


class SessionMemory:
    """MongoDB session memory following session-history-plugin pattern.

    Schema follows the Lua plugin's document structure:
    - session_id: UUID string
    - messages: array of {role, content} objects
    - system_prompt: instructions for the agent
    - token tracking: system_prompt_tokens, total_tokens
    - TTL: session_life in minutes, session_history_depth for max messages
    """

    def __init__(self):
        _validate_mongo_uri()
        self.client = get_client()
        self.db = self.client[MONGO_DB]
        self.sessions = self.db["sessions"]
        self.events = self.db["events"]
        self.decisions = self.db["decisions"]

        # Create indexes for query performance
        self.sessions.create_index([("session_id", 1)])
        self.events.create_index([("session_id", 1), ("event_type", 1)])
        self.events.create_index([("timestamp", -1)])
        self.decisions.create_index([("session_id", 1), ("timestamp", -1)])

    def create_session(
        self,
        user_id: str,
        system_prompt: str = "",
        session_life: int = 60,
        session_history_depth: int = 50,
    ) -> str:
        """Create a new session with UUID-based ID."""
        session = {
            "session_id": str(uuid4()),
            "user_id": user_id,
            "created_at": datetime.now(UTC),
            "last_active": datetime.now(UTC),
            "system_prompt": system_prompt,
            "messages": [],
            "context": {},
            "query_count": 0,
            "session_life": session_life,
            "session_history_depth": session_history_depth,
            "system_prompt_tokens": 0,
            "total_tokens": 0,
        }
        self.sessions.insert_one(session)
        return session["session_id"]

    def get_session(self, session_id: str) -> dict | None:
        """Get session by UUID session_id field."""
        return self.sessions.find_one({"session_id": session_id})

    def update_session_context(self, session_id: str, key: str, value):
        """Update session context and increment query count."""
        safe_key = key.replace(".", "_").replace("$", "_")
        self.sessions.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    f"context.{safe_key}": value,
                    "last_active": datetime.now(UTC),
                },
                "$inc": {"query_count": 1},
            },
        )

    def get_session_context(self, session_id: str) -> dict:
        """Get session context dict."""
        session = self.get_session(session_id)
        if session:
            return session.get("context", {})
        return {}

    def add_message(self, session_id: str, role: str, content: str):
        """Add a message to session history (like session-history-plugin).

        Uses atomic $push + $slice to avoid read-then-write race conditions.
        """
        depth = 50
        session = self.get_session(session_id)
        if session:
            depth = session.get("session_history_depth", 50)

        self.sessions.update_one(
            {"session_id": session_id},
            {
                "$push": {
                    "messages": {
                        "$each": [
                            {
                                "role": role,
                                "content": content,
                                "timestamp": datetime.now(UTC).isoformat(),
                            }
                        ],
                        "$slice": -depth,
                    }
                },
                "$set": {"last_active": datetime.now(UTC)},
                "$inc": {"query_count": 1},
            },
        )

    def get_messages(self, session_id: str) -> list:
        """Get all messages for a session."""
        session = self.get_session(session_id)
        if session:
            return session.get("messages", [])
        return []

    def distill_session(self, session_id: str, summary: str):
        """Replace session history with summary (like /distill-session endpoint)."""
        self.sessions.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "messages": [{"role": "system", "content": summary}],
                    "last_active": datetime.now(UTC),
                },
            },
        )

    def is_session_expired(self, session_id: str) -> bool:
        """Check if session has exceeded its TTL."""
        session = self.get_session(session_id)
        if not session:
            return True

        created = session.get("created_at")
        life = session.get("session_life", 60)
        if created:
            elapsed = (datetime.now(UTC) - created).total_seconds() / 60
            return elapsed > life
        return False

    def log_event(self, session_id: str, event_type: str, data: dict):
        """Log an event to the events collection."""
        event = {
            "session_id": session_id,
            "event_type": event_type,
            "data": data,
            "timestamp": datetime.now(UTC),
        }
        self.events.insert_one(event)

    def get_events(self, session_id: str, event_type: str | None = None) -> list:
        """Get events for a session, optionally filtered by type."""
        query = {"session_id": session_id}
        if event_type:
            query["event_type"] = event_type
        return list(self.events.find(query).sort("timestamp", -1))

    def log_decision(
        self,
        session_id: str,
        query: str,
        decision: str,
        reasoning: str,
        outcome: str | None = None,
    ):
        """Log a routing decision with reasoning."""
        record = {
            "session_id": session_id,
            "query": query,
            "decision": decision,
            "reasoning": reasoning,
            "outcome": outcome,
            "timestamp": datetime.now(UTC),
        }
        self.decisions.insert_one(record)

    def get_recent_decisions(self, session_id: str, limit: int = 10) -> list:
        """Get recent decisions for a session."""
        return list(self.decisions.find({"session_id": session_id}).sort("timestamp", -1).limit(limit))

    def get_zone_history(self, zone_name: str, limit: int = 20) -> list:
        """Get heat reading history for a zone."""
        return list(
            self.events.find({"data.zone": zone_name, "event_type": "heat_reading"}).sort("timestamp", -1).limit(limit)
        )
