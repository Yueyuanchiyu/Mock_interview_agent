from __future__ import annotations

import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict

import jwt
from redis.exceptions import RedisError

from app.core.config import settings
from app.core.exceptions import DomainError
from app.core.logging import Logger
from app.infrastructure.cache import get_redis
from app.infrastructure.mail import EmailSender
from app.repositories.auth import AuthRepository


logger = Logger.get_logger(__name__)


class AuthService:
    def __init__(
        self,
        repository: AuthRepository | None = None,
        email_sender: EmailSender | None = None,
    ) -> None:
        self.repository = repository or AuthRepository()
        self.email_sender = email_sender or EmailSender()

    def send_code(self, email: str) -> Dict[str, object]:
        user = self.repository.get_user_by_email(email)
        if not user:
            raise DomainError("该邮箱尚未注册", status_code=404, error_code="EMAIL_NOT_FOUND")

        redis_client = get_redis()
        cooldown_key = f"auth:code:cooldown:{email}"
        try:
            if not redis_client.set(cooldown_key, "1", ex=60, nx=True):
                raise DomainError(
                    "验证码发送过于频繁，请稍后再试",
                    status_code=429,
                    error_code="CODE_RATE_LIMITED",
                )
            code = f"{secrets.randbelow(1_000_000):06d}"
            redis_client.set(f"auth:code:{email}", code, ex=300)
            self.email_sender.send_code(email, code)
        except DomainError:
            raise
        except RedisError as exc:
            raise DomainError(
                "缓存服务暂时不可用",
                status_code=503,
                error_code="REDIS_UNAVAILABLE",
            ) from exc
        except Exception as exc:
            try:
                redis_client.delete(f"auth:code:{email}", cooldown_key)
            except Exception:
                pass
            logger.exception("发送验证码失败")
            raise DomainError(
                "验证码发送失败，请稍后重试",
                status_code=503,
                error_code="EMAIL_SEND_FAILED",
            ) from exc

        return {"email": email, "expires_in": 300}

    def login(self, email: str, code: str) -> Dict[str, object]:
        redis_client = get_redis()
        cached_code = redis_client.get(f"auth:code:{email}")
        if not cached_code:
            raise DomainError("验证码已过期", status_code=401, error_code="CODE_EXPIRED")
        if not hmac.compare_digest(str(cached_code), code.strip()):
            raise DomainError("验证码错误", status_code=401, error_code="CODE_INVALID")

        user = self.repository.get_user_by_email(email)
        if not user:
            raise DomainError("该邮箱尚未注册", status_code=404, error_code="EMAIL_NOT_FOUND")

        redis_client.delete(f"auth:code:{email}", f"auth:code:cooldown:{email}")
        token = self._create_token(str(user["email"]))
        return {
            "user_key": str(user["email"]),
            "user_name": str(user["user_name"]),
            "email": str(user["email"]),
            "access_token": token,
            "token_type": "bearer",
            "expires_in": settings.jwt_expire_minutes * 60,
        }

    def decode_token(self, token: str) -> str:
        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        except jwt.PyJWTError as exc:
            raise DomainError("登录状态无效或已过期", status_code=401, error_code="TOKEN_INVALID") from exc
        user_key = str(payload.get("sub", "")).strip()
        if not user_key:
            raise DomainError("登录状态无效", status_code=401, error_code="TOKEN_SUB_MISSING")
        return user_key

    @staticmethod
    def _create_token(user_key: str) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_key,
            "iat": now,
            "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
        }
        return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")

