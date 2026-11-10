from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.infrastructure.db import get_conn


class QuestionRepository:
    def get_random_question(
        self,
        role_code: str,
        exclude_ids: Optional[List[int]] = None,
    ) -> Optional[Dict[str, Any]]:
        exclude_ids = [int(item) for item in (exclude_ids or [])]
        sql = """
            SELECT id, role_code, question_type, difficulty, title, reference_answer,
                   scoring_points, followup_points, tags
            FROM question_bank
            WHERE enabled = 1 AND role_code = %s
        """
        params: List[Any] = [role_code]
        if exclude_ids:
            placeholders = ",".join(["%s"] * len(exclude_ids))
            sql += f" AND id NOT IN ({placeholders})"
            params.extend(exclude_ids)
        sql += " ORDER BY RAND() LIMIT 1"
        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchone()

    def get_question_by_id(self, question_id: int) -> Optional[Dict[str, Any]]:
        sql = """
            SELECT id, role_code, question_type, difficulty, title, reference_answer,
                   scoring_points, followup_points, tags
            FROM question_bank
            WHERE id = %s
        """
        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (question_id,))
                return cursor.fetchone()

    def get_role_name(self, role_code: str) -> Optional[str]:
        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT role_name FROM job_role WHERE role_code = %s LIMIT 1",
                    (role_code,),
                )
                row = cursor.fetchone()
                return row["role_name"] if row else None

    def get_knowledge_chunks(
        self,
        role_code: str,
        keywords: List[str],
        limit: int = 6,
    ) -> List[Dict[str, Any]]:
        keywords = [item.strip() for item in keywords if item and item.strip()][:8]
        if not keywords:
            return []
        conditions = " OR ".join(
            ["chunk_text LIKE %s OR keywords LIKE %s" for _ in keywords]
        )
        params: List[Any] = [role_code]
        for keyword in keywords:
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        sql = f"""
            SELECT id, chunk_text, keywords
            FROM knowledge_chunk
            WHERE role_code = %s AND ({conditions})
            LIMIT {max(1, min(limit, 20))}
        """
        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()

    def get_knowledge_docs(
        self,
        role_code: str,
        keywords: List[str],
        limit: int = 2,
    ) -> List[Dict[str, Any]]:
        keywords = [item.strip() for item in keywords if item and item.strip()][:8]
        if not keywords:
            return []
        conditions = " OR ".join(
            ["title LIKE %s OR content LIKE %s OR tags LIKE %s" for _ in keywords]
        )
        params: List[Any] = [role_code]
        for keyword in keywords:
            params.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])
        sql = f"""
            SELECT id, title, content, tags
            FROM knowledge_doc
            WHERE role_code = %s AND ({conditions})
            LIMIT {max(1, min(limit, 10))}
        """
        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()

