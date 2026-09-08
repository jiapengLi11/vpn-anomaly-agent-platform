import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from traffic_agent.query_context import resolve_query
from traffic_agent.knowledge_answer import answer


class QueryContextTest(unittest.TestCase):
    def test_shared_policy_cases_and_history_window(self):
        cases = json.loads((Path(__file__).resolve().parents[2] / 'shared' / 'followup-cases.json').read_text(encoding='utf-8'))
        for case in cases:
            with self.subTest(case['name']):
                result = resolve_query(case['question'], case['history'])
                self.assertEqual(result['query'], case['query'])
                self.assertEqual(result['strategy'], case['strategy'])
        history = [{'role': 'user', 'content': 'UDP'}] + [{'role': 'user', 'content': '为什么'}]*8
        self.assertEqual(resolve_query('举个例子', history)['strategy'], 'NEEDS_CONTEXT')

    def test_unresolved_never_calls_model_and_repeated_followup_keeps_topic(self):
        with patch('traffic_agent.knowledge_answer.complete') as complete:
            self.assertEqual(answer('举个例子', [], 'deepseek')['status'], 'NEEDS_CONTEXT')
            complete.assert_not_called()
        result = answer('举个例子', [{'role':'user','content':'开放集拒识'}, {'role':'user','content':'为什么呢'}], 'demo')
        self.assertEqual(result['status'], 'EXTRACTIVE')
        self.assertIn('开放集拒识', result['sources'][0]['title'])
