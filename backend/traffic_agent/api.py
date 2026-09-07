from __future__ import annotations

from typing import Any, Dict, List, Literal

from fastapi import FastAPI, Query
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


class ReviewRequest(BaseModel):
    provider: Literal["demo", "deepseek"] = "demo"
    taskId: str = "API-DEMO-001"
    candidates: List[Dict[str, Any]] = Field(default_factory=lambda: [demo_candidate()])
    featureEvidence: Dict[str, Any] = Field(default_factory=dict)
    modelEvidence: Dict[str, Any] = Field(default_factory=dict)


app = FastAPI(title="Evidence-grounded Traffic Agent", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=[f"http://{host}:{port}" for host in
                   ("localhost", "127.0.0.1") for port in (8088, 18088, 5173)],
                   allow_methods=["GET", "POST"], allow_headers=["Content-Type"])


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class QuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    provider: Literal["demo", "deepseek"] = "demo"
    history: list[HistoryMessage] = Field(default_factory=list, max_length=8)


@app.post("/api/knowledge/answer")
def knowledge_answer(request: QuestionRequest):
    return answer(request.question, bounded_history([item.model_dump() for item in request.history]), request.provider)


@app.post("/api/knowledge/answer/stream")
async def knowledge_answer_stream(request: QuestionRequest):
    async def events():
        async for item in stream_answer(request.question, [h.model_dump() for h in request.history], request.provider):
            yield f"event: {item['event']}\ndata: {json.dumps(item['data'], ensure_ascii=False)}\n\n"
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


@app.post("/api/agent/review")
def review(request: ReviewRequest):
    workflow = AgentWorkflow(retriever=retrieve_context, analyst=analyze) if request.provider == "deepseek" else build_demo_workflow()
    return workflow.invoke({
        "taskId": request.taskId,
        "rawCandidates": request.candidates,
        "featureEvidence": request.featureEvidence,
        "modelEvidence": request.modelEvidence,
        "reportSnapshot": {"riskLevel": "UNKNOWN"},
    })
