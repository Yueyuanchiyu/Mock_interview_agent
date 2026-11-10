from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.agent.graph import InterviewAgentWorkflow
from app.api.dependencies import get_current_user, get_workflow
from app.schemas.interview import (
    AgentAdviceRequest,
    FinishInterviewRequest,
    FollowupAnswerRequest,
    InterviewAnswerRequest,
    InterviewStartRequest,
)


router = APIRouter(tags=["interview"])


@router.post("/interview/start")
async def start_interview(
    payload: InterviewStartRequest,
    user_key: str = Depends(get_current_user),
    workflow: InterviewAgentWorkflow = Depends(get_workflow),
):
    data = await workflow.start(
        user_key, payload.role_code, payload.question_count
    )
    return {"code": 200, "msg": "面试开始成功", "data": data}


@router.post("/interview/answer")
async def submit_answer(
    payload: InterviewAnswerRequest,
    user_key: str = Depends(get_current_user),
    workflow: InterviewAgentWorkflow = Depends(get_workflow),
):
    data = await workflow.answer(
        user_key,
        payload.session_id,
        payload.question_no,
        payload.answer_text,
        payload.expression_metrics,
    )
    return {"code": 200, "msg": "回答已提交", "data": data}


@router.post("/interview/followup-answer")
async def submit_followup(
    payload: FollowupAnswerRequest,
    user_key: str = Depends(get_current_user),
    workflow: InterviewAgentWorkflow = Depends(get_workflow),
):
    data = await workflow.followup(
        user_key,
        payload.session_id,
        payload.question_no,
        payload.followup_no,
        payload.followup_answer,
    )
    return {"code": 200, "msg": "追问回答已处理", "data": data}


@router.get("/interview/next-question")
async def next_question(
    session_id: int = Query(..., ge=1),
    user_key: str = Depends(get_current_user),
    workflow: InterviewAgentWorkflow = Depends(get_workflow),
):
    data = await workflow.next_question(user_key, session_id)
    return {"code": 200, "msg": "获取下一题成功", "data": data}


@router.post("/interview/finish")
async def finish_interview(
    payload: FinishInterviewRequest,
    user_key: str = Depends(get_current_user),
    workflow: InterviewAgentWorkflow = Depends(get_workflow),
):
    data = await workflow.finish(user_key, payload.session_id)
    return {"code": 200, "msg": "面试已结束", "data": data}


@router.get("/interview/history")
async def history(
    user_key: str = Depends(get_current_user),
    workflow: InterviewAgentWorkflow = Depends(get_workflow),
):
    data = await workflow.history(user_key)
    return {"code": 200, "msg": "查询成功", "data": data}


@router.get("/interview/growth")
async def growth(
    role_code: str = Query(""),
    user_key: str = Depends(get_current_user),
    workflow: InterviewAgentWorkflow = Depends(get_workflow),
):
    data = await workflow.growth(user_key, role_code)
    return {"code": 200, "msg": "查询成功", "data": data}


@router.post("/agent/advice")
async def resource_advice(
    payload: AgentAdviceRequest,
    user_key: str = Depends(get_current_user),
    workflow: InterviewAgentWorkflow = Depends(get_workflow),
):
    data = await workflow.resource_advice(
        user_key, payload.session_id, payload.instruction
    )
    return {"code": 200, "msg": "资源顾问已完成", "data": data}


@router.get("/agent/state")
async def agent_state(
    session_id: int = Query(..., ge=1),
    user_key: str = Depends(get_current_user),
    workflow: InterviewAgentWorkflow = Depends(get_workflow),
):
    data = await workflow.state_snapshot(user_key, session_id)
    return {"code": 200, "msg": "查询成功", "data": data}

