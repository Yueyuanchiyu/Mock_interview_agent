from __future__ import annotations

import asyncio
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.agent.checkpoints import create_checkpointer
from app.agent.graph import InterviewAgentWorkflow
from app.api.auth_router import router as auth_router
from app.api.interview_router import router as interview_router
from app.core.config import settings
from app.core.exceptions import DomainError
from app.core.logging import Logger
from app.services.auth import AuthService


logger = Logger.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.jwt_secret == "replace-with-a-long-random-secret":
        logger.warning("JWT_SECRET 仍为默认值，请在生产环境立即替换")
    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY 未配置，LLM 能力将使用规则降级")
    async with create_checkpointer() as checkpointer:
        app.state.auth_service = AuthService()
        app.state.agent_workflow = InterviewAgentWorkflow(checkpointer)
        logger.info("Mock Interview Agent 启动完成")
        yield
    logger.info("Mock Interview Agent 已关闭")


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(interview_router)
app.mount("/static", StaticFiles(directory=str(settings.static_dir)), name="static")


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code,
            "error_code": exc.error_code,
            "msg": exc.message,
            "detail": exc.message,
        },
    )


@app.get("/")
def healthcheck():
    return {
        "code": 200,
        "msg": "服务正常",
        "data": {
            "app": settings.app_name,
            "environment": settings.app_env,
        },
    }


if __name__ == "__main__":
    import uvicorn

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )

