from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from .admission import admit_agent_context, sanitize_agent_data
from .claim_gate import validate_agent_claims
from .state import AgentState
from .tool_router import route_tools

try:
    from langgraph.graph import END, START, StateGraph
except ImportError:  # Python 3.9 compatibility path for the existing analysis environment.
    END = "__end__"
    START = "__start__"
    StateGraph = None


Retriever = Callable[[Dict[str, Any]], Dict[str, Any]]
Analyst = Callable[[Dict[str, Any]], Dict[str, Any]]


def _trace(state: AgentState, node: str, status: str, **details: Any) -> List[Dict[str, Any]]:
    return [*(state.get("trace") or []), {"sequence": len(state.get("trace") or []) + 1,
                                          "node": node, "status": status, "details": details}]


class _DeterministicCompiledGraph:
    def __init__(self, workflow: "AgentWorkflow") -> None:
        self.workflow = workflow

    def invoke(self, state: AgentState) -> AgentState:
        current = {**state}
        current.update(self.workflow.admission_node(current))
        if not current.get("admittedCandidates"):
            current.update(self.workflow.finalize_node(current))
            return current
        current.update(self.workflow.tool_router_node(current))
        if current.get('toolPlan', {}).get('status') != 'READY':
            current.update(self.workflow.finalize_node(current))
            return current
        current.update(self.workflow.retrieval_node(current))
        current.update(self.workflow.analysis_node(current))
        current.update(self.workflow.claim_gate_node(current))
        current.update(self.workflow.finalize_node(current))
        return current


class AgentWorkflow:
    def __init__(
        self,
        *,
        retriever: Optional[Retriever] = None,
        analyst: Optional[Analyst] = None,
        candidate_limit: int = 20,
    ) -> None:
        self.retriever = retriever or (lambda _context: {"items": [], "strategy": {}})
        self.analyst = analyst or (
            lambda _context: {
                "status": "SKIPPED",
                "reason": "No analyst model configured",
                "claims": [],
            }
        )
        self.candidate_limit = candidate_limit
        self.runtime_backend = "langgraph" if StateGraph is not None else "deterministic-fallback"
        self.graph = self._compile()

    def _compile(self):
        if StateGraph is None:
            return _DeterministicCompiledGraph(self)
        builder = StateGraph(AgentState)
        builder.add_node("security_admission", self.admission_node)
        builder.add_node("knowledge_retrieval", self.retrieval_node)
        builder.add_node("tool_router", self.tool_router_node)
        builder.add_node("analyst_model", self.analysis_node)
        builder.add_node("claim_gate", self.claim_gate_node)
        builder.add_node("finalize", self.finalize_node)
        builder.add_edge(START, "security_admission")
        builder.add_conditional_edges(
            "security_admission",
            lambda state: "continue" if state.get("admittedCandidates") else "skip",
            {"continue": "tool_router", "skip": "finalize"},
        )
        builder.add_conditional_edges(
            "tool_router",
            lambda state: "continue" if state.get('toolPlan', {}).get('status') == 'READY' else "skip",
            {"continue": "knowledge_retrieval", "skip": "finalize"},
        )
        builder.add_edge("knowledge_retrieval", "analyst_model")
        builder.add_edge("analyst_model", "claim_gate")
        builder.add_edge("claim_gate", "finalize")
        builder.add_edge("finalize", END)
        return builder.compile()

    def admission_node(self, state: AgentState) -> Dict[str, Any]:
        context, admission = admit_agent_context(
            state.get("taskId", ""),
            state.get("rawCandidates", []),
            feature_evidence=state.get("featureEvidence", {}),
            model_evidence=state.get("modelEvidence", {}),
            report_snapshot=state.get("reportSnapshot", {}),
            candidate_limit=self.candidate_limit,
        )
        candidates = context.get("candidates", [])
        return {
            "admittedCandidates": candidates,
            "featureEvidence": context.get("featureEvidence", {}),
            "modelEvidence": context.get("modelEvidence", {}),
            "reportSnapshot": context.get("reportSnapshot", {}),
            "admission": admission,
            "trace": _trace(state, "security_admission", admission["status"],
                            admitted=admission["admittedCandidateCount"],
                            deferred=admission["deferredCandidateCount"],
                            redacted=admission["redactedAddressCount"] + admission["redactedDomainCount"]),
        }

    def tool_router_node(self, state: AgentState) -> Dict[str, Any]:
        try:
            plan = route_tools(self._safe_context(state), state.get('requestedTools'))
            return {'toolPlan': plan, 'trace': _trace(
                state, 'tool_router', plan['status'],
                selected=len(plan['selectedTools']), rejected=len(plan['rejectedTools']),
                routerVersion=plan['routerVersion'])}
        except Exception as exc:
            plan = {'routerVersion': 'tool-router-v1', 'status': 'FAILED', 'selectedTools': [],
                    'rejectedTools': [], 'errorType': type(exc).__name__}
            return {'toolPlan': plan, 'trace': _trace(state, 'tool_router', 'FAILED',
                                                     errorType=type(exc).__name__)}

    def retrieval_node(self, state: AgentState) -> Dict[str, Any]:
        context = self._safe_context(state)
        try:
            result = self.retriever(context) or {}
            hits = sanitize_agent_data(
                str(state.get("taskId") or ""), list(result.get("items") or [])[:6]
            )
            return {
                "knowledgeHits": hits,
                "knowledgeStrategy": result.get("strategy") or {},
                "knowledgeQuery": str(result.get("query") or "")[:600],
                "trace": _trace(state, "knowledge_retrieval", "SUCCESS", hitCount=len(hits),
                                backend=result.get("knowledgeBackend", "none")),
            }
        except Exception as exc:
            return {
                "knowledgeHits": [],
                "knowledgeStrategy": {"status": "FAILED", "errorType": type(exc).__name__},
                "knowledgeQuery": "",
                "trace": _trace(state, "knowledge_retrieval", "DEGRADED", hitCount=0,
                                errorType=type(exc).__name__),
            }

    def analysis_node(self, state: AgentState) -> Dict[str, Any]:
        context = self._safe_context(state)
        context["knowledgeHits"] = state.get("knowledgeHits", [])
        context["knowledgeStrategy"] = state.get("knowledgeStrategy", {})
        context["knowledgeQuery"] = state.get("knowledgeQuery", "")
        try:
            analysis = self.analyst(context) or {}
            status = str(analysis.get("status") or "SUCCESS")
            return {
                "analysis": analysis,
                "trace": _trace(state, "analyst_model", status,
                                claimCount=len(analysis.get("claims") or [])),
            }
        except Exception as exc:
            analysis = {"status": "FAILED", "errorType": type(exc).__name__, "claims": []}
            return {
                "analysis": analysis,
                "trace": _trace(state, "analyst_model", "FAILED", errorType=type(exc).__name__),
            }

    def claim_gate_node(self, state: AgentState) -> Dict[str, Any]:
        audit = validate_agent_claims(
            state.get("analysis", {}).get("claims") or [],
            state.get("admittedCandidates", []),
            state.get("knowledgeHits", []),
        )
        return {
            "claimAudit": audit,
            "trace": _trace(state, "claim_gate", audit["status"],
                            accepted=audit["acceptedCount"], rejected=audit["rejectedCount"]),
        }

    def finalize_node(self, state: AgentState) -> Dict[str, Any]:
        no_candidates = not state.get("admittedCandidates")
        router_blocked = not no_candidates and state.get('toolPlan', {}).get('status') != 'READY'
        analysis = state.get("analysis") or {"status": "SKIPPED_TOOL_ROUTER" if router_blocked else "SKIPPED_NO_CANDIDATES",
            "reason": "Tool plan was not admitted" if router_blocked else "No flow passed Candidate Gate", "claims": []}
        audit = state.get("claimAudit") or validate_agent_claims([], [], [])
        trace = _trace(state, "finalize", "SUCCESS", securityVerdict="UNKNOWN")
        result = {
            "workflowVersion": "agent-review-v1.0",
            "runtimeBackend": self.runtime_backend,
            "status": "SKIPPED_NO_CANDIDATES" if no_candidates else analysis.get("status", "SUCCESS"),
            "securityVerdict": "UNKNOWN",
            "admission": state.get("admission", {}),
            "toolPlan": state.get('toolPlan', {}),
            "knowledgeHits": state.get("knowledgeHits", []),
            "knowledgeStrategy": state.get("knowledgeStrategy", {}),
            "knowledgeQuery": state.get("knowledgeQuery", ""),
            "analysis": analysis,
            "claimAudit": audit,
            "trace": trace,
        }
        return {"trace": trace, "result": result}

    @staticmethod
    def _safe_context(state: AgentState) -> Dict[str, Any]:
        return {
            "taskId": state.get("taskId"),
            "candidates": state.get("admittedCandidates", []),
            "featureEvidence": state.get("featureEvidence", {}),
            "modelEvidence": state.get("modelEvidence", {}),
            "reportSnapshot": state.get("reportSnapshot", {}),
            "admission": state.get("admission", {}),
        }

    def invoke(self, state: AgentState) -> Dict[str, Any]:
        final_state = self.graph.invoke({**state, "trace": list(state.get("trace") or [])})
        return final_state["result"]


def build_agent_workflow(
    *, retriever: Optional[Retriever] = None, analyst: Optional[Analyst] = None, candidate_limit: int = 20
) -> AgentWorkflow:
    return AgentWorkflow(retriever=retriever, analyst=analyst, candidate_limit=candidate_limit)
