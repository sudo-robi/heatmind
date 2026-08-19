from datetime import UTC, datetime
from uuid import uuid4

from config import MONGO_DB, MONGO_URI, _validate_mongo_uri

_client = None
_sessions: dict = {}
_events: list = []
_decisions: list = []


class _InMemoryCollection:
    """Minimal in-memory drop-in for a PyMongo collection."""

    def __init__(self, name: str):
        self._name = name
        self._docs: list[dict] = []

    def insert_one(self, doc: dict):
        doc["_id"] = len(self._docs)
        self._docs.append(doc)

    def find_one(self, query: dict) -> dict | None:
        for doc in self._docs:
            if all(doc.get(k) == v for k, v in query.items()):
                return doc
        return None

    def find(self, query: dict | None = None):
        query = query or {}

        class _Cursor:
            def __init__(self, docs, q):
                self._docs = [d for d in docs if all(d.get(k) == v for k, v in q.items())]
                self._sort_field = None
                self._sort_dir = -1
                self._limit_n = None

            def sort(self, field, direction=-1):
                self._sort_field = field
                self._sort_dir = direction
                return self

            def limit(self, n):
                self._limit_n = n
                return self

            def __iter__(self):
                docs = list(self._docs)
                if self._sort_field:
                    docs.sort(key=lambda d: d.get(self._sort_field, ""), reverse=(self._sort_dir == -1))
                if self._limit_n is not None:
                    docs = docs[: self._limit_n]
                return iter(docs)

        return _Cursor(self._docs, query)

    def update_one(self, query: dict, update: dict):
        doc = self.find_one(query)
        if doc is None:
            return
        if "$set" in update:
            for k, v in update["$set"].items():
                if "." in k:
                    parts = k.split(".")
                    current = doc
                    for part in parts[:-1]:
                        if part not in current or not isinstance(current[part], dict):
                            current[part] = {}
                        current = current[part]
                    current[parts[-1]] = v
                else:
                    doc[k] = v
        if "$inc" in update:
            for k, v in update["$inc"].items():
                doc[k] = doc.get(k, 0) + v
        if "$push" in update:
            for field, op in update["$push"].items():
                if isinstance(op, dict) and "$each" in op:
                    items = op["$each"]
                    if "$slice" in op:
                        existing = doc.get(field, [])
                        existing.extend(items)
                        doc[field] = existing[op["$slice"] :]
                    else:
                        doc.setdefault(field, []).extend(items)
                else:
                    doc.setdefault(field, []).append(op)


def get_client():
    global _client
    if not MONGO_URI:
        return None
    if _client is None:
        from pymongo import MongoClient

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
        self._mongo = get_client()
        if self._mongo:
            self.db = self._mongo[MONGO_DB]
            self.sessions = self.db["sessions"]
            self.events = self.db["events"]
            self.decisions = self.db["decisions"]
            self.sessions.create_index([("session_id", 1)])
            self.events.create_index([("session_id", 1), ("event_type", 1)])
            self.events.create_index([("timestamp", -1)])
            self.decisions.create_index([("session_id", 1), ("timestamp", -1)])
        else:
            self.sessions = _InMemoryCollection("sessions")
            self.events = _InMemoryCollection("events")
            self.decisions = _InMemoryCollection("decisions")

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

    def add_message_bulk(self, session_id: str, messages: list[tuple[str, str]]):
        """Add multiple messages at once. Each tuple is (role, content)."""
        depth = 50
        session = self.get_session(session_id)
        if session:
            depth = session.get("session_history_depth", 50)

        now_iso = datetime.now(UTC).isoformat()
        new_msgs = [{"role": role, "content": content, "timestamp": now_iso} for role, content in messages]

        self.sessions.update_one(
            {"session_id": session_id},
            {
                "$push": {
                    "messages": {
                        "$each": new_msgs,
                        "$slice": -depth,
                    }
                },
                "$set": {"last_active": datetime.now(UTC)},
                "$inc": {"query_count": len(new_msgs)},
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
            now = datetime.now(UTC)
            if created.tzinfo is None:
                now = now.replace(tzinfo=None)
            elapsed = (now - created).total_seconds() / 60
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
