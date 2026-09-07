import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from traffic_agent.knowledge import load_chunks, retrieve_context, search
from traffic_agent.api import app
from fastapi.testclient import TestClient


class KnowledgeTest(unittest.TestCase):
    def test_expected_document_and_provenance(self):
        hit = search("开放集拒识")["items"][0]
        self.assertEqual(hit["source"], "model-and-retrieval.md")
        self.assertEqual(len(hit["sourceHash"]), 64)
        self.assertTrue(hit["id"].startswith("KB-"))
        self.assertEqual(load_chunks(), load_chunks())

    def test_no_matches_and_empty_corpus(self):
        for query in ("", "xyzunmatched987", "!!!"):
            self.assertEqual(search(query)["items"], [])
        self.assertEqual(search("UDP", chunks=[])["items"], [])

    def test_context_query_uses_evidence(self):
        result = retrieve_context({"candidates": [{"evidence": [{"code": "BALANCED_EXCHANGE"}]}]})
        self.assertEqual(result["query"], "BALANCED_EXCHANGE")
        self.assertTrue(result["items"])
        self.assertEqual(result["knowledgeBackend"], "local-bm25")
        self.assertTrue(all("BALANCED_EXCHANGE" in h["content"] for h in result["items"]))

    def test_api_search_and_invalid_limits(self):
        with TestClient(app) as client:
            result = client.get("/api/knowledge/search", params={"q": "UDP", "limit": 1})
            self.assertEqual(result.status_code, 200)
            self.assertEqual(len(result.json()["items"]), 1)
            for params in ({"q": "UDP", "limit": 0}, {"q": "UDP", "limit": 21}, {"q": ""}):
                self.assertEqual(client.get("/api/knowledge/search", params=params).status_code, 422)
