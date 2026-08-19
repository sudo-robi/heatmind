"""Auto-append history middleware (Winner 1: Session History Plugin + Winner 5: Kongversation).

Automatically injects conversation history into agent context before processing.
Agents don't need to manually call get_messages() — the middleware handles it.
"""

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class AgentContext:
    query: str
    session_id: str
    history: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class HistoryMiddleware:
    def __init__(self, memory, max_history: int = 10):
        self.memory = memory
        self.max_history = max_history

    def enrich_context(self, session_id: str, query: str) -> AgentContext:
        history = []
        if session_id:
            try:
                messages = self.memory.get_messages(session_id)
                history = messages[-self.max_history :] if messages else []
            except Exception as e:
                logger.warning("Failed to load history for session %s: %s", session_id, e)

        return AgentContext(
            query=query,
            session_id=session_id,
            history=history,
            metadata={"history_count": len(history)},
        )

    def format_history_for_prompt(self, context: AgentContext) -> str:
        if not context.history:
            return ""

        lines = ["Previous conversation context:"]
        for msg in context.history[-5:]:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if len(content) > 200:
                content = content[:200] + "..."
            lines.append(f"  [{role}]: {content}")

        return "\n".join(lines)

    def record_interaction(self, session_id: str, user_query: str, agent_response: str):
        if not session_id:
            return
        try:
            self.memory.add_message(session_id, "user", user_query)
            self.memory.add_message(session_id, "assistant", agent_response)
        except Exception as e:
            logger.warning("Failed to record interaction: %s", e)
