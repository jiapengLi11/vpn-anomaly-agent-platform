from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from traffic_agent.api import app  # noqa: E402


class AgentApiTest(unittest.TestCase):
    def test_tool_catalog_exposes_only_registered_metadata(self):
        with TestClient(app) as client:
            result = client.get('/api/tools')
        self.assertEqual(result.status_code, 200)
        self.assertEqual([tool['name'] for tool in result.json()['tools']],
                         ['knowledge.search', 'analyst.review'])

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
