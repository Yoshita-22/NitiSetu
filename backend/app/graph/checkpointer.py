import asyncio
import logging
from typing import Optional
from app.core.config import settings
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger("nitsetu.checkpointer")

_singleton_checkpointer: Optional[BaseCheckpointSaver] = None


def get_checkpointer(force_memory: bool = False) -> BaseCheckpointSaver:
    """Provides the active checkpointer for workflow state persistence.

    Uses PostgreSQL checkpointer (PostgresSaver) if POSTGRES_CHECKPOINTER_URI is set.
    Otherwise gracefully falls back to MemorySaver for unit testing and local development.
    """
    global _singleton_checkpointer

    if force_memory:
        return MemorySaver()

    if _singleton_checkpointer is not None:
        return _singleton_checkpointer

    uri = settings.POSTGRES_CHECKPOINTER_URI

    if uri:
        try:
            from langgraph.checkpoint.postgres import PostgresSaver
            from psycopg_pool import ConnectionPool

            class HybridPostgresSaver(PostgresSaver):
                """Extends PostgresSaver to support asynchronous LangGraph execution (ainvoke/aget_state)."""

                async def aget_tuple(self, config):
                    return await asyncio.to_thread(self.get_tuple, config)

                async def alist(self, config, *, filter=None, before=None, limit=None):
                    return await asyncio.to_thread(self.list, config, filter=filter, before=before, limit=limit)

                async def aput(self, config, checkpoint, metadata, new_versions):
                    return await asyncio.to_thread(self.put, config, checkpoint, metadata, new_versions)

                async def aput_writes(self, config, writes, task_id):
                    return await asyncio.to_thread(self.put_writes, config, writes, task_id)

            logger.info("Initializing PostgreSQL checkpointer pool...")
            pool = ConnectionPool(conninfo=uri, min_size=1, max_size=10, kwargs={"autocommit": True})
            pg_saver = HybridPostgresSaver(pool)
            pg_saver.setup()
            _singleton_checkpointer = pg_saver
            logger.info("PostgreSQL checkpointer initialized and tables verified.")
            return _singleton_checkpointer
        except Exception as e:
            logger.warning(
                f"Failed to connect to PostgreSQL checkpointer ({e.__class__.__name__}: {e}). "
                "Falling back to in-memory checkpointer."
            )

    logger.info("Using in-memory checkpointer (MemorySaver).")
    _singleton_checkpointer = MemorySaver()
    return _singleton_checkpointer


def reset_checkpointer_for_testing():
    """Resets the singleton checkpointer between test runs."""
    global _singleton_checkpointer
    _singleton_checkpointer = None
