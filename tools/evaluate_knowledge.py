from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))

from traffic_agent.knowledge import VERSION, search  # noqa: E402
from traffic_agent.knowledge_answer import answer  # noqa: E402
from traffic_agent.query_context import resolve_query  # noqa: E402


def rounded(value):
    return round(value, 4)


def relevant_rank(items, expected):
    expected = set(expected)
    return next((index for index, item in enumerate(items, 1) if item['section'] in expected), None)


def citation_contract(result):
    allowed = {source['id'] for source in result.get('sources', [])}
    cited = [source_id for paragraph in result.get('paragraphs', []) for source_id in paragraph.get('sourceIds', [])]
    if result['status'] == 'EXTRACTIVE':
        return bool(cited) and all(source_id in allowed for source_id in cited)
    return not cited and result['status'] in {'NO_SOURCES', 'NEEDS_CONTEXT'}


def evaluate(dataset):
    retrieval, reciprocal = [], []
    contract_checks = []
    for case in dataset['retrievalCases']:
        items = search(case['question'], 3)['items']
        rank = relevant_rank(items, case['expectedSections'])
        reciprocal.append(0 if rank is None else 1 / rank)
        result = answer(case['question'], [], 'demo')
        contract_checks.append(citation_contract(result))
        retrieval.append({'id': case['id'], 'rank': rank, 'topSections': [item['section'] for item in items],
                          'passedAt3': rank is not None and rank <= 3})

    rejection = []
    for case in dataset['rejectionCases']:
        items = search(case['question'], 3)['items']
        result = answer(case['question'], [], 'demo')
        passed = not items
        contract_checks.append(citation_contract(result))
        rejection.append({'id': case['id'], 'passed': passed,
                          'unexpectedSections': [item['section'] for item in items]})

    conversations = []
    for case in dataset['conversationCases']:
        context = resolve_query(case['question'], case['history'])
        items = [] if context['strategy'] == 'NEEDS_CONTEXT' else search(context['query'], 3)['items']
        rank = relevant_rank(items, case['expectedSections']) if case['expectedSections'] else None
        passed = context['strategy'] == case['expectedStrategy'] and context['query'] == case['expectedQuery']
        passed = passed and ((rank is not None and rank <= 3) if case['expectedSections'] else not items)
        result = answer(case['question'], case['history'], 'demo')
        contract_checks.append(citation_contract(result))
        conversations.append({'id': case['id'], 'strategy': context['strategy'], 'query': context['query'],
                              'rank': rank, 'passed': passed})

    count = len(retrieval)
    metrics = {
        'hitAt1': rounded(sum(item['rank'] == 1 for item in retrieval) / count),
        'hitAt3': rounded(sum(item['passedAt3'] for item in retrieval) / count),
        'mrr': rounded(sum(reciprocal) / count),
        'outOfDomainRejection': rounded(sum(item['passed'] for item in rejection) / len(rejection)),
        'conversationResolution': rounded(sum(item['passed'] for item in conversations) / len(conversations)),
        'citationContract': rounded(sum(contract_checks) / len(contract_checks)),
    }
    gates = dataset['gates']
    gate_results = {name: {'actual': metrics[name], 'minimum': minimum,
                           'passed': metrics[name] >= minimum} for name, minimum in gates.items()}
    failures = ([{'case': item['id'], 'check': 'retrieval@3'} for item in retrieval if not item['passedAt3']] +
                [{'case': item['id'], 'check': 'out-of-domain rejection'} for item in rejection if not item['passed']] +
                [{'case': item['id'], 'check': 'conversation resolution'} for item in conversations if not item['passed']])
    return {'datasetVersion': dataset['version'], 'corpusVersion': VERSION, 'scope': dataset['scope'],
            'caseCounts': {'retrieval': count, 'rejection': len(rejection), 'conversation': len(conversations),
                           'citationContract': len(contract_checks)},
            'metrics': metrics, 'gates': gate_results, 'passed': all(g['passed'] for g in gate_results.values()),
            'failures': failures, 'details': {'retrieval': retrieval, 'rejection': rejection,
                                              'conversations': conversations}}


def markdown(report):
    metrics = report['metrics']
    rows = '\n'.join(f"| {name} | {value:.2%} | {report['gates'][name]['minimum']:.2%} | {'PASS' if report['gates'][name]['passed'] else 'FAIL'} |"
                     for name, value in metrics.items())
    ranks = '\n'.join(f"| {item['id']} | {item['rank'] or '-'} | {', '.join(item['topSections']) or '-'} |"
                      for item in report['details']['retrieval'])
    failures = '\n'.join(f"- {item['case']}: {item['check']}" for item in report['failures']) or '- None at the configured gates.'
    return f"""# Knowledge Retrieval Development Baseline

This report is generated from a small self-authored development set. It prevents known regressions; it is not an independent product-quality benchmark and must not be quoted as production accuracy.

- Dataset: `{report['datasetVersion']}`
- Corpus: `{report['corpusVersion']}`
- Cases: {report['caseCounts']['retrieval']} retrieval, {report['caseCounts']['rejection']} out-of-domain, {report['caseCounts']['conversation']} conversation, {report['caseCounts']['citationContract']} citation-contract checks
- Overall gate: **{'PASS' if report['passed'] else 'FAIL'}**

## Metrics

| Metric | Result | Regression gate | Status |
| --- | ---: | ---: | --- |
{rows}

Hit@K and MRR use the first matching labelled section. Out-of-domain rejection requires zero BM25 hits. Conversation resolution requires the expected strategy, query and top-3 section. Citation contract checks reference existence only, not semantic entailment.

## Retrieval Ranks

| Case | First relevant rank | Top sections |
| --- | ---: | --- |
{ranks}

## Gate Failures

{failures}

## Reproduce

```powershell
$env:PYTHONPATH="backend"
python tools/evaluate_knowledge.py --fail-on-gate
```

The dataset and thresholds are versioned in `evaluation/knowledge-retrieval-v1.json`. Any corpus or retrieval change should update the evidence and review failures before changing a gate.
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', type=Path, default=ROOT / 'evaluation' / 'knowledge-retrieval-v1.json')
    parser.add_argument('--json', type=Path, default=ROOT / 'frontend' / 'public' / 'demo' / 'knowledge-evaluation.json')
    parser.add_argument('--markdown', type=Path, default=ROOT / 'docs' / 'knowledge-evaluation.md')
    parser.add_argument('--fail-on-gate', action='store_true')
    args = parser.parse_args()
    dataset = json.loads(args.dataset.read_text(encoding='utf-8'))
    report = evaluate(dataset)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    args.markdown.write_text(markdown(report), encoding='utf-8')
    print(json.dumps({'passed': report['passed'], 'metrics': report['metrics']}, ensure_ascii=False))
    if args.fail_on_gate and not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
