from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import get_auth_service
from app.schemas.auth import LoginRequest, LoginResponse, SendCodeRequest
from app.services.auth import AuthService


router = APIRouter(tags=["auth"])


@router.post("/sendCode")
def send_code(
    payload: SendCodeRequest,
    service: AuthService = Depends(get_auth_service),
):
    service.send_code(str(payload.email))
    return {
        "code": 200,
        "msg": "验证码已发送",
        "data": {"email": str(payload.email), "expires_in": 300},
    }


@router.post("/login", response_model=dict)
def login(
    payload: LoginRequest,
    service: AuthService = Depends(get_auth_service),
):
    data = service.login(str(payload.email), payload.code)
    return {"code": 200, "msg": "登录成功", "data": LoginResponse(**data).model_dump()}

