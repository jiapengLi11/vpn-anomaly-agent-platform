import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))

from evaluate_answer_quality import evaluate, report_markdown, review_markdown


class AnswerQualityEvaluationTest(unittest.TestCase):
    def setUp(self):
        self.dataset = {
            'version': 'unit-v1',
            'scope': 'SYNTHETIC_CONTRACT_FIXTURE',
            'gates': {
                'statusSuccess': 1.0,
                'conceptCoverage': 1.0,
                'citationValidity': 1.0,
                'requiredSourceCoverage': 1.0,
                'forbiddenClaimAvoidance': 1.0,
                'abstentionAccuracy': 1.0,
            },
            'cases': [
                {'id': 'A', 'question': 'q', 'expected': 'ANSWER', 'requiredSections': ['Boundary'],
                 'concepts': [{'id': 'uncertainty', 'anyOf': ['不确定']}],
                 'forbiddenPhrases': ['确认恶意']},
                {'id': 'B', 'question': 'outside', 'expected': 'ABSTAIN', 'requiredSections': [],
                 'concepts': [], 'forbiddenPhrases': []},
            ],
        }
        self.run = {
            'runId': 'fixture', 'runStatus': 'COMPLETE', 'provider': 'fixture', 'model': 'fixture',
            'answerMode': 'GENERATIVE', 'humanReviewStatus': 'PENDING', 'totalTokens': 0,
            'cases': [
                {'id': 'A', 'result': {'status': 'SUCCESS', 'paragraphs': [
                    {'text': '证据仍不确定。', 'sourceIds': ['S1']}],
                    'sources': [{'id': 'S1', 'section': 'Boundary', 'content': '证据仍不确定。'}]}},
                {'id': 'B', 'result': {'status': 'NO_SOURCES', 'paragraphs': [], 'sources': []}},
            ],
        }

    def test_complete_contract_fixture_passes_automatic_checks(self):
        report = evaluate(self.dataset, self.run)
        self.assertTrue(report['automatedGatePassed'])
        self.assertTrue(all(value == 1.0 for value in report['metrics'].values()))
        self.assertIn('Human review: **PENDING**', report_markdown(report))

    def test_incomplete_run_cannot_pass_and_review_scores_stay_blank(self):
        self.run['runStatus'] = 'INCOMPLETE'
        report = evaluate(self.dataset, self.run)
        self.assertFalse(report['automatedGatePassed'])
        queue = review_markdown(self.dataset, self.run)
        self.assertIn('Faithfulness: __ / 2', queue)
        self.assertNotIn('Faithfulness: 2 / 2', queue)

    def test_repository_dataset_is_versioned_and_has_unique_cases(self):
        import json
        dataset = json.loads((ROOT / 'evaluation' / 'answer-quality-v1.json').read_text(encoding='utf-8'))
        case_ids = [case['id'] for case in dataset['cases']]
        self.assertEqual(dataset['scope'], 'SELF_AUTHORED_DEVELOPMENT_SET')
        self.assertEqual(len(case_ids), len(set(case_ids)))
        self.assertTrue(any(case['expected'] == 'ANSWER' for case in dataset['cases']))
        self.assertTrue(any(case['expected'] == 'ABSTAIN' for case in dataset['cases']))

    def test_extractive_mode_uses_its_explicit_status_contract(self):
        self.run['answerMode'] = 'EXTRACTIVE'
        self.run['cases'][0]['result']['status'] = 'EXTRACTIVE'
        self.assertTrue(evaluate(self.dataset, self.run)['automatedGatePassed'])


if __name__ == '__main__':
    unittest.main()
