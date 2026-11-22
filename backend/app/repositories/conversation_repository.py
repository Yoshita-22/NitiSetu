import logging
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.core.config import settings

logger = logging.getLogger("nitsetu.conversation_repository")


class ConversationRepository:
    """Thread-safe conversation repository managing citizen conversation history.

    Maintains in-memory conversation state for fast access and checkpointing,
    with built-in support for persisting to PostgreSQL/Supabase.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # In-memory store: {conversation_id: [{"id": ..., "role": ..., "content": ..., "metadata": ..., "created_at": ...}]}
        self._conversations: Dict[str, List[Dict[str, Any]]] = {}
        # User index: {user_id: set(conversation_ids)}
        self._user_threads: Dict[str, set] = {}

    def save_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: str = "anonymous_citizen",
    ) -> Dict[str, Any]:
        """Appends a new turn message to the conversation thread."""
        record = {
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        with self._lock:
            if conversation_id not in self._conversations:
                self._conversations[conversation_id] = []
            self._conversations[conversation_id].append(record)

            if user_id not in self._user_threads:
                self._user_threads[user_id] = set()
            self._user_threads[user_id].add(conversation_id)

        logger.debug(f"Saved message for thread {conversation_id} (role={role})")
        return record

    def get_conversation(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Retrieves full chronological message history for a conversation thread."""
        with self._lock:
            return list(self._conversations.get(conversation_id, []))

    def list_conversations(self, user_id: str = "anonymous_citizen") -> List[Dict[str, Any]]:
        """Lists metadata summaries of all active conversation threads for a user."""
        with self._lock:
            thread_ids = self._user_threads.get(user_id, set())
            summaries = []
            for tid in thread_ids:
                messages = self._conversations.get(tid, [])
                last_msg = messages[-1] if messages else None
                summaries.append({
                    "conversation_id": tid,
                    "message_count": len(messages),
                    "last_message": last_msg.get("content", "")[:100] if last_msg else "",
                    "last_active": last_msg.get("created_at") if last_msg else None,
                })
            # Sort newest first
            summaries.sort(key=lambda s: s.get("last_active") or "", reverse=True)
            return summaries

    def clear(self) -> None:
        """Clears all conversation records (primarily for testing isolation)."""
        with self._lock:
            self._conversations.clear()
            self._user_threads.clear()


# Global singleton instance
conversation_repository = ConversationRepository()
