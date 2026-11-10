from __future__ import annotations

import json
from typing import Any, Dict, List

from redis.exceptions import RedisError

from app.core.logging import Logger
from app.infrastructure.cache import get_redis


logger = Logger.get_logger(__name__)


class AgentMemoryStore:
    """Redis-backed long-term store; intentionally separate from graph state."""

    def _key(self, user_key: str) -> str:
        return f"agent:memory:profile:{user_key}"

    def load_profile(self, user_key: str) -> Dict[str, Any]:
        try:
            raw = get_redis().get(self._key(user_key))
            return json.loads(raw) if raw else {}
        except (RedisError, json.JSONDecodeError) as exc:
            logger.warning("读取长期记忆失败: %s", exc)
            return {}

    def update_profile(
        self,
        user_key: str,
        role_code: str,
        weaknesses: List[str],
        summary: str,
    ) -> None:
        profile = self.load_profile(user_key)
        profiles = profile.setdefault("roles", {})
        role_profile = profiles.setdefault(role_code, {})
        previous = role_profile.get("recurring_weaknesses", [])
        combined = list(dict.fromkeys(previous + weaknesses))
        role_profile["recurring_weaknesses"] = combined[-10:]
        role_profile["latest_summary"] = summary[:500]
        profile["updated_at"] = __import__("datetime").datetime.now().isoformat()
        try:
            get_redis().set(
                self._key(user_key),
                json.dumps(profile, ensure_ascii=False),
                ex=90 * 24 * 3600,
            )
        except RedisError as exc:
            logger.warning("写入长期记忆失败: %s", exc)

