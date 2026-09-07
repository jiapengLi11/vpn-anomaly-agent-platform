from __future__ import annotations

import json

from .agent.workflow import AgentWorkflow


def demo_candidate():
    flow_id = "192.0.2.10:51820-198.51.100.7:443-UDP"
    return {
        "flowId": flow_id,
        "decision": "CANDIDATE",
        "evidence": [
            {"id": "EV-LONG", "flowId": flow_id, "code": "LONG_SESSION",
             "kind": "RULE_EVIDENCE", "family": "duration", "strength": "MEDIUM"},
            {"id": "EV-BALANCE", "flowId": flow_id, "code": "BALANCED_EXCHANGE",
             "kind": "RULE_EVIDENCE", "family": "direction_balance", "strength": "MEDIUM"},
        ],
    }


def build_demo_workflow():
    def retriever(_context):
        return {
            "items": [{"id": "KB-BOUNDARY", "title": "Candidate interpretation boundary",
                       "source": "public-rules.md",
                       "content": "A candidate requires investigation and is not a maliciousness verdict."}],
            "strategy": {"name": "hybrid_demo"},
            "query": "encrypted traffic candidate evidence boundary",
            "knowledgeBackend": "synthetic-json",
        }

    def analyst(context):
        flow_id = context["candidates"][0]["flowId"]
        return {
            "status": "SUCCESS",
            "provider": "deterministic-demo",
            "narrative": "The session has reviewable signals and should be investigated with asset context.",
            "claims": [
                {"type": "INVESTIGATE", "flowId": flow_id, "text": "Investigate this candidate session",
                 "evidenceRefs": ["EV-LONG", "EV-BALANCE"]},
                {"type": "MALICIOUS", "flowId": flow_id, "text": "Confirmed malicious",
                 "evidenceRefs": ["EV-LONG"]},
            ],
        }

    return AgentWorkflow(retriever=retriever, analyst=analyst)


def run_demo():
    return build_demo_workflow().invoke({
        "taskId": "SYNTHETIC-DEMO-001",
        "rawCandidates": [demo_candidate()],
        "featureEvidence": {"flowCount": 128, "candidateCount": 1},
        "modelEvidence": {"backend": "DEMO_SEQUENCE_CLASSIFIER", "calibrated": False},
        "reportSnapshot": {"riskLevel": "UNKNOWN"},
    })


if __name__ == "__main__":
    print(json.dumps(run_demo(), ensure_ascii=False, indent=2))
