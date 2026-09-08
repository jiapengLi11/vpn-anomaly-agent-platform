from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from traffic_agent.api import app  # noqa: E402
from traffic_agent.demo import demo_candidate  # noqa: E402


class AgentApiTest(unittest.TestCase):
    def test_tool_catalog_exposes_only_registered_metadata(self):
        with TestClient(app) as client:
            result = client.get('/api/tools')
        self.assertEqual(result.status_code, 200)
        self.assertEqual([tool['name'] for tool in result.json()['tools']],
                         ['knowledge.search', 'analyst.review'])
        self.assertEqual(result.json()['transport'], 'mcp-bridge')
        self.assertIn('inputSchema', result.json()['tools'][0])

    def test_mcp_bridge_lists_and_calls_registered_search_tool(self):
        listed = self.client.post('/api/mcp', json={'jsonrpc': '2.0', 'id': 'list', 'method': 'tools/list'})
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()['result']['transport'], 'json-rpc-2.0')
        called = self.client.post('/api/mcp', json={
            'jsonrpc': '2.0', 'id': 'search-1', 'method': 'tools/call',
            'params': {'name': 'knowledge.search', 'arguments': {'query': 'UDP 会话特征', 'limit': 2}},
        })
        self.assertEqual(called.status_code, 200)
        self.assertEqual(called.json()['id'], 'search-1')
        self.assertFalse(called.json()['result']['isError'])
        self.assertTrue(called.json()['result']['structuredContent']['items'])

    def test_mcp_bridge_rejects_unknown_tool_and_invalid_arguments(self):
        unknown = self.client.post('/api/mcp', json={
            'id': 'unknown', 'method': 'tools/call',
            'params': {'name': 'shell.exec', 'arguments': {}},
        })
        self.assertEqual(unknown.json()['error']['code'], -32601)
        invalid = self.client.post('/api/mcp', json={
            'id': 'invalid', 'method': 'tools/call',
            'params': {'name': 'knowledge.search', 'arguments': {'query': 'UDP', 'limit': 99}},
        })
        self.assertEqual(invalid.json()['error']['code'], -32602)

    def test_mcp_review_reuses_workflow_and_billing_gate(self):
        response = self.client.post('/api/mcp', json={
            'id': 'review-1', 'method': 'tools/call',
            'params': {'name': 'analyst.review', 'arguments': {
                'requestId': 'mcp-review-test-1', 'taskId': 'MCP-TEST-1',
                'candidates': [demo_candidate()],
                'featureEvidence': {'candidateCount': 1},
            }},
        })
        self.assertEqual(response.status_code, 200)
        result = response.json()['result']['structuredContent']
        self.assertEqual(result['securityVerdict'], 'UNKNOWN')
        self.assertIn('billing', result)
        self.assertEqual([item['node'] for item in result['trace']], [
            'security_admission', 'tool_router', 'knowledge_retrieval',
            'analyst_model', 'claim_gate', 'finalize',
        ])

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_exposes_real_langgraph_runtime(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["agentRuntime"], "langgraph")
        self.assertEqual(response.json()["dataMode"], "SYNTHETIC_ONLY")

    def test_review_is_sanitized_and_rejects_forbidden_claim(self):
        response = self.client.post("/api/agent/review", json={})
        self.assertEqual(response.status_code, 200)
        result = response.json()
        serialized = json.dumps(result)
        self.assertNotIn("192.0.2.10", serialized)
        self.assertNotIn("198.51.100.7", serialized)
        self.assertEqual(result["securityVerdict"], "UNKNOWN")
        self.assertEqual(result["claimAudit"]["acceptedCount"], 1)
        self.assertEqual(result["claimAudit"]["rejectedCount"], 1)
        self.assertEqual(
            result["claimAudit"]["rejectedClaims"][0]["rejectionReason"],
            "UNSUPPORTED_CLAIM_TYPE",
        )


if __name__ == "__main__":
    unittest.main()
