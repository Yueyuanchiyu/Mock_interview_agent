from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class SendCodeRequest(BaseModel):
    email: EmailStr = Field(..., description="已注册邮箱")


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="已注册邮箱")
    code: str = Field(..., min_length=4, max_length=8, description="邮箱验证码")


class AuthUser(BaseModel):
    user_key: str
    user_name: str
    email: EmailStr


class LoginResponse(AuthUser):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

