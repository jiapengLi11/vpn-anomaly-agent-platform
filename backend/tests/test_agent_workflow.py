from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from traffic_agent.agent.admission import admit_agent_context, sanitize_agent_data
from traffic_agent.agent.claim_gate import validate_agent_claims
from traffic_agent.agent.workflow import AgentWorkflow


def candidate(index: int = 1):
    flow_id = f"192.0.2.{index}:51820-198.51.100.7:443-UDP"
    evidence_id = f"evidence-{index}"
    return {
        "flowId": flow_id,
        "decision": "CANDIDATE",
        "filePath": "/private/capture.pcap",
        "sni_values": "demo.example.invalid",
        "evidence": [
            {
                "id": evidence_id,
                "flowId": flow_id,
                "kind": "RULE_EVIDENCE",
                "strength": "MEDIUM",
                "family": "duration",
            }
        ],
    }


class SecurityAdmissionTest(unittest.TestCase):
    def test_redacts_addresses_domains_paths_and_caps_candidates(self):
        context, admission = admit_agent_context("T-safe", [candidate(i) for i in range(1, 23)])
        serialized = json.dumps(context)
        self.assertNotIn("192.0.2.", serialized)
        self.assertNotIn("198.51.100.7", serialized)
        self.assertNotIn("demo.example.invalid", serialized)
        self.assertNotIn("/private", serialized)
        self.assertEqual(len(context["candidates"]), 20)
        self.assertEqual(admission["deferredCandidateCount"], 2)
        self.assertFalse(admission["rawPcapIncluded"])

    def test_alias_is_stable_inside_one_task(self):
        context, _ = admit_agent_context("T-safe", [candidate(1), candidate(1)])
        self.assertEqual(context["candidates"][0]["flowId"], context["candidates"][1]["flowId"])

    def test_downstream_tool_output_is_sanitized(self):
        sanitized = sanitize_agent_data(
            "T-safe", {"content": "联系 203.0.113.4 或 2001:db8::7", "filePath": "/secret/rule.md",
                       "modelPath": "/models/private.bin"}
        )
        serialized = json.dumps(sanitized)
        self.assertNotIn("203.0.113.4", serialized)
        self.assertNotIn("2001:db8::7", serialized)
        self.assertNotIn("secret", serialized)
        self.assertNotIn("private.bin", serialized)


class ClaimGateTest(unittest.TestCase):
    def test_accepts_grounded_investigation_and_rejects_maliciousness(self):
        safe, _ = admit_agent_context("T-safe", [candidate(1)])
        flow_id = safe["candidates"][0]["flowId"]
        claims = [
            {"type": "INVESTIGATE", "flowId": flow_id, "text": "建议调查长会话",
             "evidenceRefs": ["evidence-1"]},
            {"type": "MALICIOUS", "flowId": flow_id, "text": "确认恶意",
             "evidenceRefs": ["evidence-1"]},
        ]
        audit = validate_agent_claims(claims, safe["candidates"], [])
        self.assertEqual(audit["acceptedCount"], 1)
        self.assertEqual(audit["rejectedCount"], 1)
        self.assertEqual(audit["securityVerdict"], "UNKNOWN")

    def test_rejects_unknown_reference(self):
        safe, _ = admit_agent_context("T-safe", [candidate(1)])
        flow_id = safe["candidates"][0]["flowId"]
        audit = validate_agent_claims(
            [{"type": "OBSERVATION", "flowId": flow_id, "text": "存在信号",
              "evidenceRefs": ["invented"]}], safe["candidates"], [])
        self.assertEqual(audit["rejectedClaims"][0]["rejectionReason"], "UNKNOWN_EVIDENCE_REFERENCE")


class AgentWorkflowTest(unittest.TestCase):
    def test_no_candidate_short_circuits_tools(self):
        retriever, analyst = Mock(), Mock()
        result = AgentWorkflow(retriever=retriever, analyst=analyst).invoke(
            {"taskId": "T-empty", "rawCandidates": []}
        )
        retriever.assert_not_called()
        analyst.assert_not_called()
        self.assertEqual(result["status"], "SKIPPED_NO_CANDIDATES")
        self.assertEqual([item["node"] for item in result["trace"]], ["security_admission", "finalize"])

    def test_runs_retrieval_analysis_claim_gate_and_trace(self):
        captured = {}

        def retriever(context):
            captured["retrieval"] = context
            return {"items": [{"id": "K-1", "content": "VPN 协议参考"}],
                    "strategy": {"name": "hybrid"}, "knowledgeBackend": "local-jsonl"}

        def analyst(context):
            captured["analysis"] = context
            flow_id = context["candidates"][0]["flowId"]
            return {"status": "SUCCESS", "narrative": "存在需调查的通信。", "claims": [
                {"type": "INVESTIGATE", "flowId": flow_id, "text": "建议调查",
                 "evidenceRefs": ["evidence-1"]},
                {"type": "BENIGN", "flowId": flow_id, "text": "确认安全", "evidenceRefs": []},
            ]}

        result = AgentWorkflow(retriever=retriever, analyst=analyst).invoke(
            {"taskId": "T-run", "rawCandidates": [candidate(1)]}
        )
        self.assertNotIn("192.0.2.1", json.dumps(captured))
        self.assertEqual(result["claimAudit"]["acceptedCount"], 1)
        self.assertEqual(result["claimAudit"]["rejectedCount"], 1)
        self.assertEqual(
            [item["node"] for item in result["trace"]],
            ["security_admission", "knowledge_retrieval", "analyst_model", "claim_gate", "finalize"],
        )

    def test_retrieval_and_analyst_failures_degrade_without_changing_verdict(self):
        def fail(_context):
            raise RuntimeError("upstream secret details")

        result = AgentWorkflow(retriever=fail, analyst=fail).invoke(
            {"taskId": "T-fail", "rawCandidates": [candidate(1)]}
        )
        self.assertEqual(result["analysis"]["status"], "FAILED")
        self.assertEqual(result["securityVerdict"], "UNKNOWN")
        self.assertNotIn("upstream secret details", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
