from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

import pymysql
from pymysql.connections import Connection
from pymysql.cursors import DictCursor

from app.core.config import settings


@contextmanager
def get_conn() -> Generator[Connection, None, None]:
    conn = pymysql.connect(
        host=settings.database_host,
        port=settings.database_port,
        user=settings.database_user,
        password=settings.database_password,
        database=settings.database_name,
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=False,
    )
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

