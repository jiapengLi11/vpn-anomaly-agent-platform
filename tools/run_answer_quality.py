from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))

from traffic_agent.deepseek import configuration  # noqa: E402
from traffic_agent.knowledge_answer import answer  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description='Freeze a reproducible answer-quality run.')
    parser.add_argument('--provider', choices=('demo', 'deepseek'), default='demo')
    parser.add_argument('--live', action='store_true', help='Required only for paid DeepSeek calls.')
    parser.add_argument('--dataset', type=Path, default=ROOT / 'evaluation' / 'answer-quality-v1.json')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--recorded-at', help='Optional fixed ISO-8601 timestamp for reproducible demo runs.')
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args()
    if args.provider == 'deepseek' and not args.live:
        parser.error('--live is required because DeepSeek ANSWER cases may incur cost')
    if args.output.exists() and not args.overwrite:
        parser.error(f'output exists: {args.output}; use a new path or --overwrite')
    deepseek_config = configuration()
    if args.provider == 'deepseek' and not deepseek_config['configured']:
        parser.error('DS_API_KEY or DEEPSEEK_API_KEY is not configured')
    config = (deepseek_config if args.provider == 'deepseek' else
              {'provider': 'demo', 'model': 'deterministic-extractive-v1'})

    dataset = json.loads(args.dataset.read_text(encoding='utf-8'))
    records, total_tokens, blocked_upstream = [], 0, None
    for case in dataset['cases']:
        if args.provider == 'deepseek' and case['expected'] == 'ANSWER' and blocked_upstream:
            result = {'status': 'NOT_RUN', 'paragraphs': [], 'sources': [],
                      'reason': 'UPSTREAM_CIRCUIT_OPEN', 'upstreamStatus': blocked_upstream}
        else:
            result = answer(case['question'], [], args.provider)
        if result['status'] == 'FAILED' and result.get('upstreamStatus') in {401, 402, 403, 429}:
            blocked_upstream = result['upstreamStatus']
        total_tokens += result.get('usage', {}).get('total_tokens', 0)
        records.append({'id': case['id'], 'question': case['question'], 'result': result})
        print(json.dumps({'id': case['id'], 'status': result['status'],
                          'elapsedMs': result.get('elapsedMs'),
                          'tokens': result.get('usage', {}).get('total_tokens', 0)}, ensure_ascii=False))
    expected_statuses = {
        'ANSWER': {'EXTRACTIVE'} if args.provider == 'demo' else {'SUCCESS'},
        'ABSTAIN': {'NO_SOURCES', 'NEEDS_CONTEXT', 'INSUFFICIENT'},
    }
    complete = all(record['result']['status'] in expected_statuses[case['expected']]
                   for case, record in zip(dataset['cases'], records))
    recorded_at = args.recorded_at or datetime.now(timezone.utc).isoformat(timespec='seconds')
    run = {'runId': args.output.stem, 'recordedAt': recorded_at,
           'datasetVersion': dataset['version'], 'scope': dataset['scope'], 'provider': config['provider'],
           'model': config['model'], 'runStatus': 'COMPLETE' if complete else 'INCOMPLETE',
           'answerMode': 'EXTRACTIVE' if args.provider == 'demo' else 'GENERATIVE',
           'upstreamCircuitStatus': 'OPEN' if blocked_upstream else 'CLOSED',
           'upstreamStatus': blocked_upstream, 'totalTokens': total_tokens, 'cases': records,
           'humanReviewStatus': 'PENDING'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(run, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'runId': run['runId'], 'runStatus': run['runStatus'],
                      'caseCount': len(records), 'totalTokens': total_tokens}, ensure_ascii=False))


if __name__ == '__main__':
    main()
