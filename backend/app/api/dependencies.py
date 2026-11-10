from __future__ import annotations

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.agent.graph import InterviewAgentWorkflow
from app.core.exceptions import DomainError
from app.services.auth import AuthService


_bearer = HTTPBearer(auto_error=False)


def get_auth_service(request: Request) -> AuthService:
    return request.app.state.auth_service


def get_workflow(request: Request) -> InterviewAgentWorkflow:
    return request.app.state.agent_workflow


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise DomainError(
            "请先登录",
            status_code=401,
            error_code="AUTH_REQUIRED",
        )
    return request.app.state.auth_service.decode_token(credentials.credentials)

