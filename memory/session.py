from datetime import UTC, datetime
from uuid import uuid4

from config import MONGO_DB, MONGO_URI, _validate_mongo_uri

_client = None
_sessions: dict = {}
_events: list = []
_decisions: list = []


def _match_query(doc: dict, query: dict) -> bool:
    for k, v in query.items():
        if "." in k:
            parts = k.split(".")
            current = doc
            for part in parts:
                if not isinstance(current, dict):
                    return False
                current = current.get(part)
                if current is None:
                    return False
            if current != v:
                return False
        else:
            if doc.get(k) != v:
                return False
    return True


class _InMemoryCollection:
    """Minimal in-memory drop-in for a PyMongo collection."""

    def __init__(self, name: str):
        self._name = name
        self._docs: list[dict] = []

    def insert_one(self, doc: dict):
        doc["_id"] = len(self._docs)
        self._docs.append(doc)

    def _match_query(self, doc: dict, query: dict) -> bool:
        return _match_query(doc, query)

    def find_one(self, query: dict) -> dict | None:
        for doc in self._docs:
            if _match_query(doc, query):
                return doc
        return None

    def find(self, query: dict | None = None):
        query = query or {}

        class _Cursor:
            def __init__(self, docs, q):
                self._docs = [d for d in docs if _match_query(d, q)]
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

    def drop(self):
        self._docs.clear()


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
    - patterns: extracted learning patterns from past decisions
    """

    def __init__(self):
        _validate_mongo_uri()
        self._mongo = get_client()
        if self._mongo:
            self.db = self._mongo[MONGO_DB]
            self.sessions = self.db["sessions"]
            self.events = self.db["events"]
            self.decisions = self.db["decisions"]
            self.patterns = self.db["patterns"]
            self.sessions.create_index([("session_id", 1)])
            self.events.create_index([("session_id", 1), ("event_type", 1)])
            self.events.create_index([("timestamp", -1)])
            self.decisions.create_index([("session_id", 1), ("timestamp", -1)])
            self.patterns.create_index([("pattern_key", 1)])
            self.patterns.create_index([("zone", 1), ("timestamp", -1)])
        else:
            self.sessions = _InMemoryCollection("sessions")
            self.events = _InMemoryCollection("events")
            self.decisions = _InMemoryCollection("decisions")
            self.patterns = _InMemoryCollection("patterns")

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
        extra: dict | None = None,
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
        if extra:
            record.update(extra)
        self.decisions.insert_one(record)

    def get_recent_decisions(self, session_id: str, limit: int = 10) -> list:
        """Get recent decisions for a session."""
        return list(self.decisions.find({"session_id": session_id}).sort("timestamp", -1).limit(limit))

    def get_audit_trail(self, limit: int = 20) -> list:
        """Get the most recent autonomous decisions across all sessions."""
        return list(self.decisions.find().sort("timestamp", -1).limit(limit))

    def get_zone_history(self, zone_name: str, limit: int = 20) -> list:
        """Get heat reading history for a zone."""
        return list(
            self.events.find({"data.zone": zone_name, "event_type": "heat_reading"}).sort("timestamp", -1).limit(limit)
        )

    # ── Learning patterns ────────────────────────────────────────────────

    def record_pattern(self, pattern: dict):
        """Store an extracted learning pattern."""
        self.patterns.insert_one(pattern)

    def get_successful_patterns(self, zone: str = "", query_type: str = "", limit: int = 10) -> list:
        """Get successful patterns, optionally filtered by zone and/or query_type."""
        query = {"outcome": {"$in": ["success", "completed"]}}
        if zone:
            query["zone"] = zone
        if query_type:
            query["query_type"] = query_type
        return list(self.patterns.find(query).sort("timestamp", -1).limit(limit))

    def get_all_patterns(self, limit: int = 50) -> list:
        """Get all stored patterns."""
        return list(self.patterns.find().sort("timestamp", -1).limit(limit))

    def record_outcome(self, trace_id: str, outcome: str, feedback: str | None = None):
        """Record outcome and optional user feedback for a trace.

        Updates the pattern with matching trace_id, and also updates the decision record.
        """
        update_fields = {"outcome": outcome}
        if feedback:
            update_fields["user_feedback"] = feedback

        # Update any patterns with this trace_id
        self.patterns.update_one(
            {"trace_id": trace_id},
            {"$set": update_fields},
        )
        # Also update the decision record
        self.decisions.update_one(
            {"trace_id": trace_id},
            {"$set": update_fields},
        )

    def get_pattern_stats(self) -> dict:
        """Get aggregate statistics about learned patterns."""
        all_patterns = list(self.patterns.find())
        if not all_patterns:
            return {
                "total": 0,
                "zones": 0,
                "top_tools": [],
                "success_rate": 0,
                "feedback_positive": 0,
                "feedback_negative": 0,
            }

        zones = set(p.get("zone", "") for p in all_patterns)
        tool_counts: dict[str, int] = {}
        for p in all_patterns:
            for t in p.get("tools_used", []):
                tool_counts[t] = tool_counts.get(t, 0) + 1
        top_tools = sorted(tool_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        successful = sum(1 for p in all_patterns if p.get("outcome") in ("success", "completed"))
        positive = sum(1 for p in all_patterns if p.get("user_feedback") == "positive")
        negative = sum(1 for p in all_patterns if p.get("user_feedback") == "negative")

        return {
            "total": len(all_patterns),
            "zones": len(zones),
            "top_tools": top_tools,
            "success_rate": round(successful / len(all_patterns), 3) if all_patterns else 0,
            "feedback_positive": positive,
            "feedback_negative": negative,
        }
