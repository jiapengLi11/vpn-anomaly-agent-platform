from __future__ import annotations

from typing import Any, Dict, List, Literal
import uuid

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import json
from pydantic import BaseModel, Field

from .demo import build_demo_workflow, demo_candidate
from .knowledge import search
from .deepseek import analyze, configuration
from .agent.workflow import AgentWorkflow
from .knowledge import retrieve_context
from .knowledge_answer import answer
from .knowledge_stream import stream_answer, bounded_history
from .agent.tool_router import public_catalog
from .billing import BillingDenied, billing

DEMO_USER_ID = 'demo-user'


class ReviewRequest(BaseModel):
    requestId: str = Field(default_factory=lambda: str(uuid.uuid4()), min_length=8, max_length=80)
    provider: Literal["demo", "deepseek"] = "demo"
    taskId: str = "API-DEMO-001"
    candidates: List[Dict[str, Any]] = Field(default_factory=lambda: [demo_candidate()])
    featureEvidence: Dict[str, Any] = Field(default_factory=dict)
    modelEvidence: Dict[str, Any] = Field(default_factory=dict)
    requestedTools: List[str] = Field(default_factory=list, max_length=8)


app = FastAPI(title="Evidence-grounded Traffic Agent", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=[f"http://{host}:{port}" for host in
                   ("localhost", "127.0.0.1") for port in (8088, 18088, 5173)],
                   allow_methods=["GET", "POST"], allow_headers=["Content-Type"])


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class QuestionRequest(BaseModel):
    requestId: str = Field(default_factory=lambda: str(uuid.uuid4()), min_length=8, max_length=80)
    question: str = Field(min_length=1, max_length=500)
    provider: Literal["demo", "deepseek"] = "demo"
    history: list[HistoryMessage] = Field(default_factory=list, max_length=8)


class PaymentOrderRequest(BaseModel):
    channel: Literal['WECHAT', 'ALIPAY']
    amountFen: Literal[1000, 3000, 10000]


def authorize_or_402(request_id, operation):
    try:
        return billing.authorize(DEMO_USER_ID, request_id, operation)
    except BillingDenied as exc:
        raise HTTPException(status_code=402, detail={'code': exc.code, 'message': str(exc)}) from exc


def token_counts(result):
    usage = result.get('usage') or {}
    return usage.get('prompt_tokens', 0), usage.get('completion_tokens', 0)


def billable_answer(result):
    return result.get('status') in {'SUCCESS', 'EXTRACTIVE', 'NO_SOURCES', 'INSUFFICIENT'}


@app.post("/api/knowledge/answer")
def knowledge_answer(request: QuestionRequest):
    authorization = authorize_or_402(request.requestId, 'KNOWLEDGE_QA')
    try:
        result = answer(request.question, bounded_history([item.model_dump() for item in request.history]), request.provider)
        if billable_answer(result):
            result['billing'] = billing.settle(authorization, *token_counts(result))
        else:
            billing.release(authorization)
        return result
    except Exception:
        billing.release(authorization)
        raise


@app.post("/api/knowledge/answer/stream")
async def knowledge_answer_stream(request: QuestionRequest):
    authorization = authorize_or_402(request.requestId, 'KNOWLEDGE_QA')
    async def events():
        closed = False
        try:
            async for item in stream_answer(request.question, [h.model_dump() for h in request.history], request.provider):
                if item['event'] == 'done':
                    if billable_answer(item['data']):
                        item['data']['billing'] = billing.settle(authorization, *token_counts(item['data']))
                    else:
                        billing.release(authorization)
                    closed = True
                elif item['event'] == 'error':
                    billing.release(authorization)
                    closed = True
                yield f"event: {item['event']}\ndata: {json.dumps(item['data'], ensure_ascii=False)}\n\n"
        finally:
            if not closed:
                billing.release(authorization)
    return StreamingResponse(events(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"})


@app.get("/api/knowledge/search")
def knowledge_search(q: str = Query(min_length=1, max_length=500),
                     limit: int = Query(default=6, ge=1, le=20)):
    return search(q, limit)


@app.get("/health")
def health():
    workflow = build_demo_workflow()
    return {"status": "UP", "agentRuntime": workflow.runtime_backend, "dataMode": "SYNTHETIC_ONLY",
            "analyst": configuration()}


@app.get('/api/tools')
def tools_catalog():
    return public_catalog()


@app.get('/api/billing/summary')
def billing_summary():
    return billing.summary(DEMO_USER_ID)


@app.post('/api/billing/orders')
def create_payment_order(request: PaymentOrderRequest):
    return billing.create_order(DEMO_USER_ID, request.channel, request.amountFen)


@app.post('/api/billing/orders/{order_id}/simulate-paid')
def simulate_payment(order_id: str):
    try:
        return {'order': billing.simulate_paid(DEMO_USER_ID, order_id),
                'summary': billing.summary(DEMO_USER_ID)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail='沙箱订单不存在。') from exc


@app.post("/api/agent/review")
def review(request: ReviewRequest):
    authorization = authorize_or_402(request.requestId, 'ANALYSIS')
    try:
        workflow = AgentWorkflow(retriever=retrieve_context, analyst=analyze) if request.provider == "deepseek" else build_demo_workflow()
        result = workflow.invoke({
            "taskId": request.taskId,
            "rawCandidates": request.candidates,
            "featureEvidence": request.featureEvidence,
            "modelEvidence": request.modelEvidence,
            "reportSnapshot": {"riskLevel": "UNKNOWN"},
            "requestedTools": request.requestedTools,
        })
        analysis = result.get('analysis') or {}
        result['billing'] = billing.settle(authorization, *token_counts(analysis))
        return result
    except Exception:
        billing.release(authorization)
        raise
