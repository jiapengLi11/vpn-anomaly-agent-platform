"""Real provider streaming; draft text is never treated as a validated answer."""
import asyncio
import json
import os
import time
from pathlib import Path

import httpx
from pydantic_core import from_json

from .deepseek import configuration
from .knowledge import search
from .knowledge_answer import Answer, answer, validate_answer


def bounded_history(history, budget=8000):
    """Keep recent complete messages, with an explicit character (not token) budget."""
    kept = []
    for message in reversed(history[-8:]):
        if len(message['content']) > budget:
            break
        kept.append(message)
        budget -= len(message['content'])
    return list(reversed(kept))


def draft_text(raw):
    try:
        partial = from_json(raw, allow_partial='trailing-strings')
        paragraphs = partial.get('paragraphs', []) if isinstance(partial, dict) else []
        return '\n\n'.join(p['text'] for p in paragraphs if isinstance(p, dict) and isinstance(p.get('text'), str))
    except ValueError:
        return ''


async def stream_answer(question, history, provider):
    started = time.monotonic()
    history = bounded_history(history)
    yield {'event': 'status', 'data': {'stage': 'retrieving', 'historyMessages': len(history),
                                      'historyCharacters': sum(len(h['content']) for h in history)}}
    if provider == 'demo':
        yield {'event': 'done', 'data': answer(question, history, provider)}
        return
    previous = [h['content'] for h in history if h['role'] == 'user']
    query = question if len(question) >= 16 or not previous else previous[-1] + ' ' + question
    sources = search(query, 4)['items']
    base = {'sources': sources, 'query': query, 'provider': provider,
            'citationValidation': 'REFERENCE_IDS_ONLY', 'followUps': []}
    yield {'event': 'sources', 'data': sources}
    config = configuration()
    if not sources or not config['configured']:
        yield {'event': 'done', 'data': {**base, 'status': 'NO_SOURCES' if not sources else 'SKIPPED',
                'paragraphs': [], 'message': '没有相关资料。' if not sources else '请在后端配置 DS_API_KEY。'}}
        return
    skill = Path(__file__).with_name('skills') / 'vpn-knowledge-qa' / 'SKILL.md'
    raw, preview, finish, first_ms, usage = '', '', None, None, {}
    try:
        prompt = skill.read_text(encoding='utf-8').split('---', 2)[-1].strip()
        async with asyncio.timeout(65):
            async with httpx.AsyncClient(timeout=httpx.Timeout(30, connect=10), follow_redirects=False) as client:
                async with client.stream('POST', 'https://api.deepseek.com/chat/completions',
                    headers={'Authorization': f"Bearer {os.getenv('DS_API_KEY') or os.environ['DEEPSEEK_API_KEY']}"},
                    json={'model': config['model'], 'stream': True, 'stream_options': {'include_usage': True},
                          'response_format': {'type': 'json_object'}, 'max_tokens': 2200,
                          'messages': [{'role': 'system', 'content': prompt}, {'role': 'user', 'content': json.dumps(
                              {'question': question, 'history': history, 'sources': sources}, ensure_ascii=False)}]}) as response:
                    response.raise_for_status()
                    yield {'event': 'status', 'data': {'stage': 'generating'}}
                    async for line in response.aiter_lines():
                        if not line.startswith('data:'):
                            continue
                        data = line[5:].strip()
                        if data == '[DONE]':
                            break
                        chunk = json.loads(data)
                        if chunk.get('usage'):
                            usage = {k: v for k, v in chunk['usage'].items() if k in
                                     {'prompt_tokens', 'completion_tokens', 'total_tokens'} and type(v) is int}
                        for choice in chunk.get('choices', []):
                            if choice.get('finish_reason'):
                                finish = choice['finish_reason']
                            raw += choice.get('delta', {}).get('content') or ''
                        if len(raw) > 48000:
                            raise ValueError('Output limit exceeded')
                        text = draft_text(raw)
                        if text and text != preview:
                            first_ms = first_ms if first_ms is not None else round((time.monotonic() - started) * 1000)
                            preview = text
                            yield {'event': 'draft', 'data': {'text': text, 'validation': 'UNVALIDATED'}}
        if finish != 'stop':
            raise ValueError('Incomplete stream')
        parsed = Answer.model_validate_json(raw).model_dump()
        result = validate_answer(base, {**parsed, 'model': config['model'], 'usage': usage,
                                       'elapsedMs': round((time.monotonic() - started) * 1000)})
        result['firstDraftMs'] = first_ms
        yield {'event': 'done', 'data': result}
    except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError, AttributeError, TimeoutError) as exc:
        yield {'event': 'error', 'data': {'status': 'FAILED', 'errorType': type(exc).__name__,
                                         'message': '生成中断或校验失败，草稿已撤回，请重试。'}}
    # Cancellation deliberately propagates so a disconnected browser closes the upstream stream.
