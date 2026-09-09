"""Small explainable intent router for the public orchestration demo."""
from __future__ import annotations

import re

from .planning_catalog import planning_candidates

ROUTER_VERSION = "intent-router-public-v1"


def _normalized(value):
    return re.sub(r"\s+", "", str(value or "").lower())


def resolve_intent(message, context=None):
    if not message or not str(message).strip():
        raise ValueError("message must not be blank")
    if len(message) > 2000:
        raise ValueError("message exceeds 2000 characters")
    context = dict(context or {})
    text = _normalized(message)
    pcap_signals = [token for token in ("pcap", "抓包", "流量研判", "异常流量", "研判报告") if token in text]
    knowledge_signals = [token for token in ("为什么", "是什么", "如何", "怎么", "原理", "特征") if token in text]
    if context.get("fileId") or pcap_signals:
        intent, domain, signals = "PCAP_INVESTIGATION", "TRAFFIC_ANALYSIS", pcap_signals
        missing = [] if context.get("fileId") else ["fileId"]
        score = 8 + len(signals) * 2 + (6 if context.get("fileId") else 0)
    elif knowledge_signals:
        intent, domain, signals, missing = "KNOWLEDGE_QA", "KNOWLEDGE", knowledge_signals, []
        score = 5 + len(signals) * 2
    else:
        return {
            "routerVersion": ROUTER_VERSION, "status": "NEEDS_CLARIFICATION",
            "intent": "UNRESOLVED", "domain": "UNKNOWN", "confidenceBand": "LOW",
            "heuristicScore": 0, "matchedSignals": [], "missingSlots": [],
            "toolCandidates": [], "executionPlanCreated": False,
            "clarification": "请说明需要分析 PCAP，还是查询流量与协议知识。",
        }
    return {
        "routerVersion": ROUTER_VERSION,
        "status": "NEEDS_CLARIFICATION" if missing else "RESOLVED",
        "intent": intent, "domain": domain,
        "confidenceBand": "HIGH" if score >= 12 else "MEDIUM",
        "heuristicScore": score, "matchedSignals": signals[:8],
        "slots": {key: context[key] for key in ("fileId", "fileName") if context.get(key)},
        "missingSlots": missing, "toolCandidates": planning_candidates(intent),
        "toolCandidateScope": "PUBLIC_REGISTERED_TOOLS_ONLY", "executionPlanCreated": False,
        "selectionMethod": "RULE_AND_CONTEXT", "llmUsed": False,
        "clarification": "缺少必要参数：fileId" if missing else None,
    }
