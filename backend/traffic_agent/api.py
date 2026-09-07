from __future__ import annotations

from typing import Any, Dict, List

from fastapi import FastAPI
from pydantic import BaseModel, Field

from .demo import build_demo_workflow, demo_candidate


class ReviewRequest(BaseModel):
    taskId: str = "API-DEMO-001"
    candidates: List[Dict[str, Any]] = Field(default_factory=lambda: [demo_candidate()])
    featureEvidence: Dict[str, Any] = Field(default_factory=dict)
    modelEvidence: Dict[str, Any] = Field(default_factory=dict)


app = FastAPI(title="Evidence-grounded Traffic Agent", version="1.0.0")


@app.get("/health")
def health():
    workflow = build_demo_workflow()
    return {"status": "UP", "agentRuntime": workflow.runtime_backend, "dataMode": "SYNTHETIC_ONLY"}


@app.post("/api/agent/review")
def review(request: ReviewRequest):
    return build_demo_workflow().invoke({
        "taskId": request.taskId,
        "rawCandidates": request.candidates,
        "featureEvidence": request.featureEvidence,
        "modelEvidence": request.modelEvidence,
        "reportSnapshot": {"riskLevel": "UNKNOWN"},
    })
