from __future__ import annotations

from typing import Any, Dict, List, Literal
import time
import uuid

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
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
from .mcp_bridge import McpBridgeError, dispatch
from .agent.run_coordinator import AgentRunCoordinator

DEMO_USER_ID = 'demo-user'
AGENT_RUN_COORDINATOR = AgentRunCoordinator()


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


class McpRpcRequest(BaseModel):
    jsonrpc: Literal['2.0'] = '2.0'
    id: str | int | None = None
    method: str = Field(min_length=1, max_length=100)
    params: Dict[str, Any] = Field(default_factory=dict)


class AgentPlanRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    context: Dict[str, Any] = Field(default_factory=dict)
    requestedTools: List[str] = Field(default_factory=list, max_length=10)


class AgentRunRequest(AgentPlanRequest):
    requestId: str | None = Field(default=None, min_length=8, max_length=100)


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


@app.post('/api/mcp')
def mcp_rpc(request: McpRpcRequest):
    authorization = None
    if request.method == 'tools/call' and request.params.get('name') == 'analyst.review':
        arguments = request.params.get('arguments') or {}
        request_id = arguments.get('requestId') or f'mcp-{request.id or uuid.uuid4()}'
        authorization = authorize_or_402(request_id, 'ANALYSIS')
    try:
        result = dispatch(request.method, request.params)
        if authorization is not None:
            content = result.get('structuredContent') or {}
            content['billing'] = billing.settle(authorization, *token_counts(content.get('analysis') or {}))
            result['structuredContent'] = content
            result['content'][0]['text'] = json.dumps(result['structuredContent'], ensure_ascii=False)
        return {'jsonrpc': '2.0', 'id': request.id, 'result': result}
    except McpBridgeError as exc:
        billing.release(authorization)
        response = {'jsonrpc': '2.0', 'id': request.id,
                    'error': {'code': exc.code, 'message': str(exc)}}
        if exc.data is not None:
            response['error']['data'] = exc.data
        return response
    except Exception:
        billing.release(authorization)
        raise


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


@app.post("/api/agent/plans/preview")
def preview_agent_plan(request: AgentPlanRequest):
    return AGENT_RUN_COORDINATOR.preview(request.message, context=request.context,
                                         requested_tools=request.requestedTools)


@app.post("/api/agent/runs")
def create_agent_run(request: AgentRunRequest, background_tasks: BackgroundTasks):
    run = AGENT_RUN_COORDINATOR.create_run(
        request.message, context=request.context, requested_tools=request.requestedTools,
        request_id=request.requestId)
    if run["status"] == "PENDING":
        background_tasks.add_task(AGENT_RUN_COORDINATOR.execute, run["runId"])
    return run


@app.get("/api/agent/runs/{run_id}")
def get_agent_run(run_id: str):
    try:
        return AGENT_RUN_COORDINATOR.get_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="agent run not found") from exc


@app.post("/api/agent/runs/{run_id}/cancel")
def cancel_agent_run(run_id: str):
    try:
        return AGENT_RUN_COORDINATOR.cancel(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="agent run not found") from exc


@app.get("/api/agent/runs/{run_id}/events")
def stream_agent_run_events(run_id: str, after: int = Query(default=0, ge=0)):
    try:
        AGENT_RUN_COORDINATOR.get_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="agent run not found") from exc

    def events():
        sequence, deadline = after, time.monotonic() + 60
        while time.monotonic() < deadline:
            batch = AGENT_RUN_COORDINATOR.events_after(run_id, sequence)
            for event in batch:
                sequence = event["sequence"]
                yield (f"id: {sequence}\nevent: {event['type']}\n"
                       f"data: {json.dumps(event, ensure_ascii=False)}\n\n")
            run = AGENT_RUN_COORDINATOR.get_run(run_id)
            if AGENT_RUN_COORDINATOR.is_terminal(run["status"]) and not batch:
                break
            time.sleep(.1)

    return StreamingResponse(events(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"})
