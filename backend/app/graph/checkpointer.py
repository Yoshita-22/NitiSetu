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

            logger.info("Initializing PostgreSQL checkpointer pool...")
            pool = ConnectionPool(conninfo=uri, min_size=1, max_size=10)
            pg_saver = PostgresSaver(pool)
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
