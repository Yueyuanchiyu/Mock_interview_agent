from __future__ import annotations

from typing import Any, Dict, List

from app.infrastructure.db import get_conn


class ResourceRepository:
    def search(
        self,
        role_code: str,
        keywords: List[str],
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 30))
        keywords = [item.strip() for item in keywords if item and item.strip()][:8]

        with get_conn() as conn:
            with conn.cursor() as cursor:
                if keywords:
                    conditions = " OR ".join(
                        [
                            "tags LIKE %s OR title LIKE %s OR content LIKE %s"
                            for _ in keywords
                        ]
                    )
                    params: List[Any] = [role_code]
                    for keyword in keywords:
                        params.extend(
                            [f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"]
                        )
                    cursor.execute(
                        f"""
                        SELECT id, title, resource_type, content, link, tags
                        FROM learning_resource
                        WHERE role_code = %s AND ({conditions})
                        ORDER BY id DESC
                        LIMIT {safe_limit}
                        """,
                        params,
                    )
                    rows = cursor.fetchall()
                    if rows:
                        return rows

                cursor.execute(
                    f"""
                    SELECT id, title, resource_type, content, link, tags
                    FROM learning_resource
                    WHERE role_code = %s
                    ORDER BY id DESC
                    LIMIT {safe_limit}
                    """,
                    (role_code,),
                )
                return cursor.fetchall()

    def save_recommendations(
        self,
        session_id: int,
        resources: List[Dict[str, Any]],
    ) -> None:
        if not resources:
            return
        with get_conn() as conn:
            with conn.cursor() as cursor:
                for item in resources:
                    cursor.execute(
                        """
                        INSERT INTO recommendation_record
                            (session_id, resource_id, reason, priority)
                        VALUES (%s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            reason = VALUES(reason),
                            priority = VALUES(priority)
                        """,
                        (
                            session_id,
                            item["id"],
                            item.get("reason", ""),
                            item.get("priority", 99),
                        ),
                    )

