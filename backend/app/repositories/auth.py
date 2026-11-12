from __future__ import annotations

from typing import Any, Dict, Optional

from app.infrastructure.db import get_conn


class AuthRepository:
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT user_id, user_name, email FROM user_info WHERE email = %s LIMIT 1",
                    (email,),
                )
                return cursor.fetchone()

    def create_user(self, email: str, user_name: str) -> Optional[Dict[str, Any]]:
        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO user_info (user_name, email) VALUES (%s, %s)",
                    (user_name, email),
                )
        return self.get_user_by_email(email)

