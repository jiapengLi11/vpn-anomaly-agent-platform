from __future__ import annotations

from typing import Any, Dict, List, TypedDict


class AgentState(TypedDict, total=False):
    taskId: str
    rawCandidates: List[Dict[str, Any]]
    featureEvidence: Dict[str, Any]
    modelEvidence: Dict[str, Any]
    reportSnapshot: Dict[str, Any]
    admittedCandidates: List[Dict[str, Any]]
    admission: Dict[str, Any]
    requestedTools: List[str]
    toolPlan: Dict[str, Any]
    knowledgeHits: List[Dict[str, Any]]
    knowledgeStrategy: Dict[str, Any]
    knowledgeQuery: str
    analysis: Dict[str, Any]
    claimAudit: Dict[str, Any]
    trace: List[Dict[str, Any]]
    result: Dict[str, Any]
