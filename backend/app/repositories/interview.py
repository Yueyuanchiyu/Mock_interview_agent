from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.infrastructure.db import get_conn


class InterviewRepository:
    def create_session(
        self,
        user_key: str,
        role_code: str,
        question_count: int,
    ) -> int:
        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO interview_session
                        (user_key, role_code, total_questions, current_question_no, status)
                    VALUES (%s, %s, %s, 1, 'in_progress')
                    """,
                    (user_key, role_code, question_count),
                )
                return int(cursor.lastrowid)

    def get_session(self, session_id: int) -> Optional[Dict[str, Any]]:
        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM interview_session WHERE id = %s LIMIT 1",
                    (session_id,),
                )
                return cursor.fetchone()

    def create_round(
        self,
        session_id: int,
        question_no: int,
        question_id: int,
        question_text: str,
    ) -> None:
        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO interview_round
                        (session_id, question_no, question_id, question_text)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        question_id = VALUES(question_id),
                        question_text = VALUES(question_text)
                    """,
                    (session_id, question_no, question_id, question_text),
                )

    def get_round(self, session_id: int, question_no: int) -> Optional[Dict[str, Any]]:
        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT * FROM interview_round
                    WHERE session_id = %s AND question_no = %s
                    LIMIT 1
                    """,
                    (session_id, question_no),
                )
                return cursor.fetchone()

    def update_round_analysis(
        self,
        session_id: int,
        question_no: int,
        answer_text: str,
        analysis: Dict[str, Any],
    ) -> None:
        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE interview_round
                    SET answer_text = %s,
                        followup_question = %s,
                        technical_score = %s,
                        depth_score = %s,
                        logic_score = %s,
                        role_match_score = %s,
                        speech_rate_score = %s,
                        clarity_score = %s,
                        confidence_score = %s,
                        strengths = %s,
                        weaknesses = %s,
                        suggestions = %s
                    WHERE session_id = %s AND question_no = %s
                    """,
                    (
                        answer_text,
                        analysis.get("followup_question", ""),
                        analysis.get("technical_score", 0),
                        analysis.get("depth_score", 0),
                        analysis.get("logic_score", 0),
                        analysis.get("role_match_score", 0),
                        analysis.get("speech_rate_score", 0),
                        analysis.get("clarity_score", 0),
                        analysis.get("confidence_score", 0),
                        "\n".join(analysis.get("strengths", [])),
                        "\n".join(analysis.get("weaknesses", [])),
                        "\n".join(analysis.get("suggestions", [])),
                        session_id,
                        question_no,
                    ),
                )

    def update_current_question(self, session_id: int, question_no: int) -> None:
        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE interview_session SET current_question_no = %s WHERE id = %s",
                    (question_no, session_id),
                )

    def get_used_question_ids(self, session_id: int) -> List[int]:
        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT question_id FROM interview_round WHERE session_id = %s",
                    (session_id,),
                )
                return [int(row["question_id"]) for row in cursor.fetchall()]

    def get_user_used_question_ids(
        self,
        user_key: str,
        role_code: str,
        limit: int = 200,
    ) -> List[int]:
        safe_limit = max(1, min(int(limit), 1000))
        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT DISTINCT r.question_id
                    FROM interview_round r
                    INNER JOIN interview_session s ON r.session_id = s.id
                    WHERE s.user_key = %s AND s.role_code = %s
                    ORDER BY r.question_id DESC
                    LIMIT {safe_limit}
                    """,
                    (user_key, role_code),
                )
                return [
                    int(row["question_id"])
                    for row in cursor.fetchall()
                    if row.get("question_id") is not None
                ]

    def create_followup_turn(
        self,
        session_id: int,
        question_no: int,
        followup_no: int,
        question_text: str,
    ) -> None:
        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO interview_followup_turn
                        (session_id, question_no, followup_no, question_text)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE question_text = VALUES(question_text)
                    """,
                    (session_id, question_no, followup_no, question_text),
                )

    def update_followup_answer(
        self,
        session_id: int,
        question_no: int,
        followup_no: int,
        answer_text: str,
    ) -> None:
        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE interview_followup_turn
                    SET answer_text = %s
                    WHERE session_id = %s AND question_no = %s AND followup_no = %s
                    """,
                    (answer_text, session_id, question_no, followup_no),
                )
                if followup_no == 1:
                    cursor.execute(
                        """
                        UPDATE interview_round
                        SET followup_answer = %s
                        WHERE session_id = %s AND question_no = %s
                        """,
                        (answer_text, session_id, question_no),
                    )

    def list_followup_turns(
        self,
        session_id: int,
        question_no: int,
    ) -> List[Dict[str, Any]]:
        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, session_id, question_no, followup_no,
                           question_text, answer_text, created_time
                    FROM interview_followup_turn
                    WHERE session_id = %s AND question_no = %s
                    ORDER BY followup_no ASC
                    """,
                    (session_id, question_no),
                )
                return cursor.fetchall()

    def list_rounds(self, session_id: int) -> List[Dict[str, Any]]:
        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT * FROM interview_round
                    WHERE session_id = %s
                    ORDER BY question_no ASC
                    """,
                    (session_id,),
                )
                return cursor.fetchall()

    def finish_session(self, session_id: int, total_score: float) -> None:
        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE interview_session
                    SET status = 'finished',
                        end_time = COALESCE(end_time, NOW()),
                        total_score = %s
                    WHERE id = %s
                    """,
                    (total_score, session_id),
                )

    def save_report(
        self,
        session_id: int,
        summary: str,
        report: Dict[str, Any],
        report_docx_url: str,
    ) -> None:
        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO interview_report
                        (session_id, summary, report_json, report_docx_url)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        summary = VALUES(summary),
                        report_json = VALUES(report_json),
                        report_docx_url = VALUES(report_docx_url)
                    """,
                    (
                        session_id,
                        summary,
                        json.dumps(report, ensure_ascii=False),
                        report_docx_url,
                    ),
                )

    def get_report(self, session_id: int) -> Optional[Dict[str, Any]]:
        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT * FROM interview_report
                    WHERE session_id = %s
                    LIMIT 1
                    """,
                    (session_id,),
                )
                return cursor.fetchone()

    def list_history(self, user_key: str) -> List[Dict[str, Any]]:
        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT s.id, s.user_key, s.role_code, s.total_questions,
                           s.status, s.start_time, s.end_time, s.total_score,
                           r.report_docx_url
                    FROM interview_session s
                    LEFT JOIN interview_report r ON s.id = r.session_id
                    WHERE s.user_key = %s
                    ORDER BY s.id DESC
                    """,
                    (user_key,),
                )
                return cursor.fetchall()

    def get_growth(
        self,
        user_key: str,
        role_code: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        sql = """
            SELECT s.id, s.role_code, s.start_time,
                   COALESCE(s.total_score, 0) AS total_score,
                   ROUND(AVG(COALESCE(r.technical_score, 0)), 2) AS technical_score,
                   ROUND(AVG(COALESCE(r.depth_score, 0)), 2) AS depth_score,
                   ROUND(AVG(COALESCE(r.logic_score, 0)), 2) AS logic_score,
                   ROUND(AVG(COALESCE(r.role_match_score, 0)), 2) AS role_match_score,
                   ROUND(AVG(COALESCE(r.speech_rate_score, 0)), 2) AS speech_rate_score,
                   ROUND(AVG(COALESCE(r.clarity_score, 0)), 2) AS clarity_score,
                   ROUND(AVG(COALESCE(r.confidence_score, 0)), 2) AS confidence_score
            FROM interview_session s
            LEFT JOIN interview_round r ON s.id = r.session_id
            WHERE s.user_key = %s AND s.status = 'finished'
        """
        params: List[Any] = [user_key]
        if role_code:
            sql += " AND s.role_code = %s"
            params.append(role_code)
        sql += """
            GROUP BY s.id, s.role_code, s.start_time, s.total_score
            ORDER BY s.start_time ASC
        """
        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()

