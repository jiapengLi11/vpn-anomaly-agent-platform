from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from traffic_agent.demo import run_demo  # noqa: E402


def main():
    agent = run_demo()
    flow_id = agent["claimAudit"]["acceptedClaims"][0]["flowId"]
    task_id = "SYNTHETIC-DEMO-001"
    now = "2026-09-07T02:52:20+00:00"
    gate = {"policyVersion": "candidate-v1.0-demo", "totalFlowCount": 128, "candidateCount": 1,
            "observeCount": 18, "passCount": 109, "candidateRatio": 0.0078,
            "note": "Candidate means investigate, not malicious."}
    summary = {
        "taskId": task_id, "fileName": "synthetic_traffic_sample.pcap", "flowCount": 128,
        "protocolDistribution": {"TCP": 83, "UDP": 45}, "candidateGate": gate,
        "requestedModelRoute": "SEQUENCE_ENCODER", "fusionMode": "FEATURE_PLUS_SEQUENCE_ENCODER",
        "modelExecution": {"actualModelBackend": "SEQUENCE_ENCODER_DEMO", "adapterReady": True,
                           "note": "Synthetic classifier output for interface demonstration only."},
        "agentWorkflowStatus": agent["status"], "agentRuntimeBackend": agent["runtimeBackend"],
        "agentAcceptedClaimCount": 1, "agentRejectedClaimCount": 1, "knowledgeHitCount": 1,
        "llmReportStatus": "SUCCESS", "llmCandidateInputCount": 1, "llmCandidateDeferredCount": 0,
    }
    report = {
        "executiveSummary": "128 synthetic sessions were parsed; one candidate requires human review.",
        "conclusion": "One investigation candidate was found. Candidate does not mean malicious.",
        "riskLevel": "UNKNOWN", "riskLevelDisplay": "待人工复核", "securityVerdict": "UNKNOWN",
        "suggestions": ["Review asset ownership and historical connections.",
                        "Correlate with authorized threat-intelligence sources."],
        "agent": agent, "llm": agent["analysis"], "knowledgeHits": agent["knowledgeHits"],
        "knowledgeStrategy": agent["knowledgeStrategy"], "knowledgeQuery": agent["knowledgeQuery"],
        "candidateGate": gate,
    }
    decision = {"flowId": flow_id, "decision": "CANDIDATE", "reason": "MULTIPLE_EVIDENCE_FAMILIES",
                "evidence": agent["claimAudit"]["acceptedClaims"], "securityVerdict": "UNKNOWN"}
    task = {"taskId": task_id, "fileId": "SYNTHETIC", "fileName": summary["fileName"], "status": "SUCCESS",
            "stage": "COMPLETED", "progress": 100, "createdAt": now, "completedAt": now,
            "elapsedSeconds": 2, "modelType": "SEQUENCE_ENCODER",
            "fusionMode": "FEATURE_PLUS_SEQUENCE_ENCODER", "enableLlmReport": True}
    preview = {**task, "summary": summary, "report": report, "humanReadableSummary": report["conclusion"],
               "ruleHits": [], "topRiskFlows": [], "artifacts": [], "modelExtension": {},
               "offlineDecisions": [decision]}
    output = ROOT / "frontend" / "public" / "demo" / "workspace.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"mode": "SYNTHETIC_READ_ONLY", "generatedAt": now,
                                  "description": "Synthetic, non-production showcase data.",
                                  "tasks": [task], "previews": {task_id: preview}},
                                 ensure_ascii=False), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
