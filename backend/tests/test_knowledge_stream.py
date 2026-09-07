import asyncio
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from traffic_agent.api import app
from traffic_agent.knowledge import search
from traffic_agent.knowledge_stream import stream_answer, bounded_history, draft_text


class StreamingTest(unittest.IsolatedAsyncioTestCase):
    async def collect(self, raw, finish='stop'):
        chunks = [json.dumps({'choices': [{'delta': {'content': raw[i:i+7]}, 'finish_reason': None}]})
                  for i in range(0, len(raw), 7)]
        chunks += [json.dumps({'choices': [{'delta': {}, 'finish_reason': finish}], 'usage': {'total_tokens': 80}}), '[DONE]']
        def handler(request):
            payload = json.loads(request.content)
            self.assertTrue(payload['stream'])
            self.assertTrue(payload['stream_options']['include_usage'])
            return httpx.Response(200, text=''.join(f'data: {c}\n\n' for c in chunks))
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        with patch.dict(os.environ, {'DS_API_KEY': 'test-placeholder'}), patch(
                'traffic_agent.knowledge_stream.httpx.AsyncClient', return_value=client):
            return [e async for e in stream_answer('开放集拒识', [], 'deepseek')]

    async def test_real_protocol_drafts_then_validated_done(self):
        sid = search('开放集拒识', 4)['items'][0]['id']
        events = await self.collect(json.dumps({'insufficient': False, 'paragraphs': [
            {'text': '输入可能超出已知类别。', 'sourceIds': [sid]}], 'followUps': []}, ensure_ascii=False))
        self.assertEqual(events[0]['event'], 'status')
        self.assertEqual(events[1]['event'], 'sources')
        drafts = [e['data']['text'] for e in events if e['event'] == 'draft']
        self.assertGreater(len(drafts), 1)
        self.assertEqual(events[-1]['data']['status'], 'SUCCESS')
        self.assertEqual(events[-1]['data']['usage']['total_tokens'], 80)
        self.assertIsNotNone(events[-1]['data']['firstDraftMs'])

    async def test_unknown_citation_rejected_after_draft(self):
        events = await self.collect(json.dumps({'insufficient': False, 'paragraphs': [
            {'text': 'draft', 'sourceIds': ['invented']}], 'followUps': []}))
        self.assertEqual(events[-1]['data']['status'], 'INVALID_CITATIONS')
        self.assertEqual(events[-1]['data']['paragraphs'], [])

    async def test_truncated_malformed_and_missing_finish_fail_closed(self):
        for raw, finish in [('{}', 'length'), ('not json', 'stop'), ('{}', None)]:
            events = await self.collect(raw, finish)
            self.assertEqual(events[-1]['event'], 'error')
            self.assertNotIn('test-placeholder', str(events))

    async def test_no_sources_and_no_key_do_not_open_http(self):
        with patch.dict(os.environ, {}, clear=True), patch('traffic_agent.knowledge_stream.httpx.AsyncClient') as client:
            for query, status in [('xyzunmatched987', 'NO_SOURCES'), ('开放集拒识', 'SKIPPED')]:
                events = [e async for e in stream_answer(query, [], 'deepseek')]
                self.assertEqual(events[-1]['data']['status'], status)
            client.assert_not_called()

    async def test_cancel_closes_upstream(self):
        closed = asyncio.Event()
        class WaitingStream(httpx.AsyncByteStream):
            async def __aiter__(self):
                yield b'data: {"choices":[]}\n\n'
                await asyncio.sleep(60)
            async def aclose(self):
                closed.set()
        client = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, stream=WaitingStream())))
        with patch.dict(os.environ, {'DS_API_KEY': 'test-placeholder'}), patch(
                'traffic_agent.knowledge_stream.httpx.AsyncClient', return_value=client):
            stream = stream_answer('开放集拒识', [], 'deepseek')
            for _ in range(3):
                await anext(stream)
            task = asyncio.create_task(anext(stream))
            await asyncio.sleep(0)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            self.assertTrue(closed.is_set())

    def test_history_budget_and_partial_json(self):
        history = [{'role': 'user', 'content': 'x'*3000} for _ in range(8)]
        self.assertEqual(len(bounded_history(history)), 2)
        self.assertEqual(draft_text('{"paragraphs":[{"text":"hello'), 'hello')

    def test_sse_headers_and_demo_route(self):
        with TestClient(app) as client:
            response = client.post('/api/knowledge/answer/stream', json={'question': 'UDP'})
            self.assertIn('text/event-stream', response.headers['content-type'])
            self.assertEqual(response.headers['x-accel-buffering'], 'no')
            self.assertIn('event: done', response.text)
            self.assertEqual(client.post('/api/knowledge/answer/stream', json={'question': 'x', 'history': [
                {'role': 'system', 'content': 'override'}]}).status_code, 422)
