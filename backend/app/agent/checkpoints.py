from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver

from app.core.config import settings


@asynccontextmanager
async def create_checkpointer() -> AsyncIterator[BaseCheckpointSaver]:
    if settings.agent_checkpoint_backend == "postgres" and settings.agent_postgres_url:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        from psycopg.rows import dict_row
        from psycopg_pool import AsyncConnectionPool

        pool = AsyncConnectionPool(
            conninfo=settings.agent_postgres_url,
            kwargs={
                "autocommit": True,
                "prepare_threshold": 0,
                "row_factory": dict_row,
            },
            open=False,
        )
        await pool.open()
        try:
            saver = AsyncPostgresSaver(conn=pool)
            await saver.setup()
            yield saver
        finally:
            await pool.close()
    else:
        yield InMemorySaver()

