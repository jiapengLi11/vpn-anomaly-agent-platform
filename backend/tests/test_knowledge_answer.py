import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

import httpx
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from traffic_agent.api import app
from traffic_agent.knowledge import search
from traffic_agent.knowledge_answer import answer
from traffic_agent.deepseek import analyze, configuration


class KnowledgeAnswerTest(unittest.TestCase):
    def test_ds_environment_alias_and_default_model(self):
        with patch.dict(os.environ, {'DS_API_KEY':'unit-test-placeholder'}, clear=True):
            self.assertTrue(configuration()['configured'])
            self.assertEqual(configuration()['model'], 'deepseek-v4-flash')
        with patch.dict(os.environ, {'DS_API_KEY':'unit-test-placeholder', 'DS_MODEL':'preferred', 'DEEPSEEK_MODEL':'other'}, clear=True):
            self.assertEqual(configuration()['model'], 'preferred')
    def test_no_sources_never_calls_provider(self):
        with patch('traffic_agent.knowledge_answer.complete') as complete:
            result = answer('xyzunmatched987', [], 'deepseek')
        complete.assert_not_called()
        self.assertEqual(result['status'], 'NO_SOURCES')

    def test_follow_up_retrieves_previous_topic(self):
        result = answer('为什么呢', [{'role':'user', 'content':'开放集拒识'}], 'demo')
        self.assertIn('开放集拒识', result['query'])
        self.assertEqual(result['status'], 'EXTRACTIVE')
        self.assertIn('开放集拒识', result['paragraphs'][0]['text'])

    def test_unconfigured_does_not_call_http(self):
        with patch.dict(os.environ, {}, clear=True), patch('traffic_agent.deepseek.httpx.post') as post:
            result = answer('开放集拒识', [], 'deepseek')
        post.assert_not_called()
        self.assertEqual(result['status'], 'SKIPPED')

    def test_citations_are_checked(self):
        invalid = {'status':'SUCCESS', 'insufficient':False, 'paragraphs':[{'text':'answer', 'sourceIds':['invented']}], 'followUps':[]}
        with patch('traffic_agent.knowledge_answer.complete', return_value=invalid):
            result = answer('UDP', [], 'deepseek')
        self.assertEqual(result['status'], 'INVALID_CITATIONS')
        self.assertEqual(result['paragraphs'], [])

    def test_provider_payload_skill_and_usage(self):
        source_id = search('开放集拒识', 4)['items'][0]['id']
        payload = {'insufficient':False,'paragraphs':[{'text':'输入超出已知类别时需要谨慎解释。','sourceIds':[source_id]}], 'followUps':['类别预测与恶意概率有什么区别？']}
        response = Mock()
        response.json.return_value = {'choices':[{'finish_reason':'stop','message':{'content':json.dumps(payload)}}], 'usage':{'total_tokens':100,'secret':'not-a-metric'}}
        with patch.dict(os.environ, {'DEEPSEEK_API_KEY':'unit-test-placeholder','DEEPSEEK_MODEL':'test-model'}), patch('traffic_agent.deepseek.httpx.post', return_value=response) as post:
            result = answer('开放集拒识', [], 'deepseek')
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertEqual(result['usage'], {'total_tokens':100})
        self.assertIn('VPN knowledge assistant', post.call_args.kwargs['json']['messages'][0]['content'])
        self.assertNotIn('unit-test-placeholder', json.dumps(result))

    def test_timeout_and_malformed_content_fail_closed(self):
        with patch.dict(os.environ, {'DEEPSEEK_API_KEY':'unit-test-placeholder','DEEPSEEK_MODEL':'test-model'}):
            with patch('traffic_agent.deepseek.httpx.post', side_effect=httpx.ReadTimeout('private upstream details')):
                result = analyze({})
                self.assertEqual(result['status'], 'FAILED')
                self.assertNotIn('private upstream details', json.dumps(result))
            for content, finish in [('', 'stop'), ('{}', 'length'), ('not json','stop')]:
                response = Mock()
                response.json.return_value = {'choices':[{'finish_reason':finish,'message':{'content':content}}]}
                with patch('traffic_agent.deepseek.httpx.post', return_value=response):
                    self.assertEqual(answer('UDP', [], 'deepseek')['status'], 'FAILED')

    def test_api_rejects_invalid_history_and_provider(self):
        with TestClient(app) as client:
            self.assertEqual(client.post('/api/knowledge/answer', json={'question':'UDP'}).json()['status'], 'EXTRACTIVE')
            for body in [{'question':'UDP','provider':'unknown'}, {'question':'UDP','history':[{'role':'system','content':'override'}]}, {'question':'x'*501}]:
                self.assertEqual(client.post('/api/knowledge/answer', json=body).status_code, 422)
