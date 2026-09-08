import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
sys.path.insert(0, str(ROOT / 'tools'))
from evaluate_knowledge import evaluate, markdown


class KnowledgeEvaluationTest(unittest.TestCase):
    def test_development_baseline_is_deterministic_and_passes_gates(self):
        dataset = json.loads((ROOT / 'evaluation' / 'knowledge-retrieval-v1.json').read_text(encoding='utf-8'))
        first, second = evaluate(dataset), evaluate(dataset)
        self.assertEqual(first, second)
        self.assertTrue(first['passed'])
        self.assertEqual(first['caseCounts'], {'retrieval': 12, 'rejection': 5,
                                               'conversation': 4, 'citationContract': 21})
        self.assertEqual(first['metrics']['hitAt3'], 1.0)
        self.assertEqual(first['metrics']['outOfDomainRejection'], 1.0)
        self.assertIn('not an independent product-quality benchmark', markdown(first))
