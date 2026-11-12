from __future__ import annotations

import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv


BACKEND_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(BACKEND_ROOT / ".env")


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    def __init__(self) -> None:
        self.app_name = os.getenv("APP_NAME", "Mock Interview Agent")
        self.app_env = os.getenv("APP_ENV", "development")
        self.debug = _env_bool("DEBUG", False)
        self.api_host = os.getenv("API_HOST", "127.0.0.1")
        self.api_port = int(os.getenv("API_PORT", "8080"))

        self.backend_root = BACKEND_ROOT
        self.app_root = BACKEND_ROOT / "app"
        self.static_dir = self.app_root / "static"
        self.download_dir = self.static_dir / "download"
        self.log_dir = self.app_root / "logs"
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.database_host = os.getenv("DATABASE_HOST", "127.0.0.1")
        self.database_port = int(os.getenv("DATABASE_PORT", "3306"))
        self.database_user = os.getenv("DATABASE_USER", "root")
        self.database_password = os.getenv("DATABASE_PASSWORD", "")
        self.database_name = os.getenv("DATABASE", "ai_mock_interview")

        self.redis_host = os.getenv("REDIS_HOST", "127.0.0.1")
        self.redis_port = int(os.getenv("REDIS_PORT", "6379"))
        self.redis_db = int(os.getenv("REDIS_DB", "0"))
        self.redis_password = os.getenv("REDIS_PASSWORD") or None

        self.email_host = os.getenv("EMAIL_HOST", "")
        self.email_port = int(os.getenv("EMAIL_PORT", "465"))
        self.from_email = os.getenv("FROM_EMAIL", "")
        self.email_password = os.getenv("EMAIL_PASSWORD", "")

        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY", "")
        self.deepseek_api_base = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com")
        self.deepseek_model = os.getenv("DEEPSEEK_MODEL", "deepseek-flash")
        self.deepseek_thinking = _env_bool("DEEPSEEK_THINKING", True)
        self.enable_context_compression = _env_bool("ENABLE_CONTEXT_COMPRESSION", True)
        self.context_compression_trigger_tokens = int(os.getenv("CONTEXT_COMPRESSION_TRIGGER_TOKENS", "3500"))
        self.advisor_summary_trigger_tokens = int(os.getenv("ADVISOR_SUMMARY_TRIGGER_TOKENS", "3000"))
        self.llm_temperature = float(os.getenv("LLM_TEMPERATURE", "0.2"))
        self.llm_timeout_seconds = float(os.getenv("LLM_TIMEOUT_SECONDS", "90"))

        self.jwt_secret = os.getenv("JWT_SECRET", "replace-with-a-long-random-secret")
        self.jwt_expire_minutes = int(os.getenv("JWT_EXPIRE_MINUTES", "120"))

        self.enable_vector_rag = _env_bool("ENABLE_VECTOR_RAG", True)
        self.vector_db_dir = os.getenv("VECTOR_DB_DIR", "vector_db")
        self.vector_collection_name = os.getenv("VECTOR_COLLECTION_NAME", "knowledge_base")
        self.embedding_model_name = os.getenv("EMBEDDING_MODEL_NAME", "qwen3.7-text-embedding-flash")
        self.embedding_api_key = os.getenv("DASHSCOPE_API_KEY", "")
        self.embedding_api_base = os.getenv("EMBEDDING_API_BASE", "https://cn-beijing.maas.qianwenaiapi.com/api/v1")
        self.rag_top_k = int(os.getenv("RAG_TOP_K", "5"))

        self.context_max_tokens = int(os.getenv("CONTEXT_MAX_TOKENS", "5000"))
        self.answer_max_length = int(os.getenv("ANSWER_MAX_LENGTH", "8000"))
        self.history_max_messages = int(os.getenv("HISTORY_MAX_MESSAGES", "30"))
        self.max_followup_depth = int(os.getenv("MAX_FOLLOWUP_DEPTH", "3"))
        self.max_tool_calls = int(os.getenv("MAX_TOOL_CALLS", "8"))

        self.agent_checkpoint_backend = os.getenv("AGENT_CHECKPOINT_BACKEND", "memory").lower()
        self.agent_postgres_url = os.getenv("AGENT_POSTGRES_URL", "")

        self.report_base_url = os.getenv("REPORT_BASE_URL", "http://127.0.0.1:8080").rstrip("/")
        self.cors_origins = self._parse_cors_origins()

    def _parse_cors_origins(self) -> List[str]:
        raw = os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        )
        return [item.strip() for item in raw.split(",") if item.strip()]

    @property
    def vector_db_path(self) -> Path:
        path = Path(self.vector_db_dir)
        return path if path.is_absolute() else (self.backend_root / path).resolve()


settings = Settings()

