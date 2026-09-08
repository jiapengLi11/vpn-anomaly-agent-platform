from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def rounded(value):
    return round(value, 4)


def evaluate(dataset, run):
    by_id = {item['id']: item for item in run['cases']}
    details, concepts, citation_checks, source_checks, forbidden_checks = [], [], [], [], []
    answer_status, abstentions = [], []
    for case in dataset['cases']:
        record = by_id.get(case['id'])
        if not record:
            details.append({'id': case['id'], 'passed': False, 'error': 'MISSING_RUN_CASE'})
            continue
        result = record['result']
        text = '\n'.join(p.get('text', '') for p in result.get('paragraphs', []))
        allowed = {source['id'] for source in result.get('sources', [])}
        cited = {ref for p in result.get('paragraphs', []) for ref in p.get('sourceIds', [])}
        cited_sections = {source['section'] for source in result.get('sources', []) if source['id'] in cited}
        concept_results = {concept['id']: any(term.lower() in text.lower() for term in concept['anyOf'])
                           for concept in case['concepts']}
        forbidden_hits = [phrase for phrase in case['forbiddenPhrases'] if phrase.lower() in text.lower()]
        if case['expected'] == 'ANSWER':
            expected_answer_status = 'EXTRACTIVE' if run.get('answerMode') == 'EXTRACTIVE' else 'SUCCESS'
            status_ok = result['status'] == expected_answer_status
            citation_ok = bool(cited) and cited.issubset(allowed)
            source_ok = set(case['requiredSections']).issubset(cited_sections)
            answer_status.append(status_ok)
            citation_checks.append(citation_ok)
            source_checks.append(source_ok)
            concepts.extend(concept_results.values())
            forbidden_checks.append(not forbidden_hits)
            passed = status_ok and citation_ok and source_ok and not forbidden_hits and all(concept_results.values())
        else:
            passed = result['status'] in {'NO_SOURCES', 'NEEDS_CONTEXT', 'INSUFFICIENT'} and not result.get('paragraphs')
            abstentions.append(passed)
        details.append({'id': case['id'], 'expected': case['expected'], 'status': result['status'],
                        'passed': passed, 'concepts': concept_results,
                        'missingConcepts': [name for name, ok in concept_results.items() if not ok],
                        'forbiddenHits': forbidden_hits, 'citedSections': sorted(cited_sections)})
    metrics = {
        'statusSuccess': rounded(sum(answer_status) / len(answer_status)),
        'conceptCoverage': rounded(sum(concepts) / len(concepts)),
        'citationValidity': rounded(sum(citation_checks) / len(citation_checks)),
        'requiredSourceCoverage': rounded(sum(source_checks) / len(source_checks)),
        'forbiddenClaimAvoidance': rounded(sum(forbidden_checks) / len(forbidden_checks)),
        'abstentionAccuracy': rounded(sum(abstentions) / len(abstentions)),
    }
    run_status = run.get('runStatus', 'UNKNOWN')
    gates = {name: {'actual': metrics[name], 'minimum': minimum, 'passed': metrics[name] >= minimum}
             for name, minimum in dataset['gates'].items()}
    return {'datasetVersion': dataset['version'], 'runId': run['runId'], 'provider': run['provider'],
            'model': run['model'], 'answerMode': run.get('answerMode', 'GENERATIVE'),
            'runStatus': run_status, 'scope': dataset['scope'],
            'caseCount': len(dataset['cases']),
            'answerCaseCount': len(answer_status), 'abstentionCaseCount': len(abstentions),
            'totalTokens': run.get('totalTokens'), 'metrics': metrics, 'gates': gates,
            'automatedGatePassed': run_status == 'COMPLETE' and all(item['passed'] for item in gates.values()),
            'humanReviewStatus': run.get('humanReviewStatus', 'PENDING'), 'details': details}


def report_markdown(report):
    rows = '\n'.join(f"| {name} | {value:.2%} | {report['gates'][name]['minimum']:.2%} | {'PASS' if report['gates'][name]['passed'] else 'FAIL'} |"
                     for name, value in report['metrics'].items())
    cases = '\n'.join(f"| {item['id']} | {item['expected']} | {item['status']} | {', '.join(item['missingConcepts']) or '-'} | {', '.join(item['forbiddenHits']) or '-'} |"
                      for item in report['details'])
    mode_note = ("This run is a deterministic extractive baseline: the response copies retrieved source passages. "
                 "Its 100% contract score validates the evaluation pipeline, citations, and abstention behavior; "
                 "it is not a score for LLM generation quality."
                 if report['answerMode'] == 'EXTRACTIVE' else
                 "This is a generative model run and still requires human review before any quality claim.")
    return f"""# Answer Quality Development Baseline

This report evaluates a frozen model run with deterministic heuristics. It is not an independent benchmark, and automated PASS does not mean the prose is factually entailed by its citations.

- Dataset: `{report['datasetVersion']}`
- Run: `{report['runId']}`
- Provider/model: `{report['provider']} / {report['model']}`
- Answer mode: **{report['answerMode']}**
- Run status: **{report['runStatus']}**
- Cases: {report['answerCaseCount']} answered, {report['abstentionCaseCount']} abstained
- Recorded tokens: {report['totalTokens']}
- Automated gate: **{'PASS' if report['automatedGatePassed'] else 'FAIL'}**
- Human review: **{report['humanReviewStatus']}**

> {mode_note}

## Automated Metrics

| Metric | Result | Gate | Status |
| --- | ---: | ---: | --- |
{rows}

Concept coverage is keyword/synonym matching. Citation validity checks IDs, and required-source coverage checks cited sections. Neither proves semantic entailment.

## Case Diagnostics

| Case | Expected | Status | Missing concepts | Forbidden hits |
| --- | --- | --- | --- | --- |
{cases}

An incomplete run can never pass the automated gate, even if its partial metrics happen to meet thresholds. The automated gate is suitable for regression only. Do not report it as RAG accuracy, faithfulness, or hallucination rate.
"""


def review_markdown(dataset, run):
    by_id = {item['id']: item for item in run['cases']}
    blocks = []
    for case in dataset['cases']:
        result = by_id[case['id']]['result']
        answer = '\n\n'.join(p.get('text', '') for p in result.get('paragraphs', [])) or '(abstained)'
        sources = '\n'.join(f"- `{s['id']}` {s['section']}: {s['content']}" for s in result.get('sources', [])) or '- None'
        blocks.append(f"""## {case['id']}: {case['question']}

**Expected behavior:** {case['expected']}
**Observed status:** {result['status']}

**Answer**

{answer}

**Retrieved sources**

{sources}

**Human rubric (0-2 each; leave evidence in notes)**

- [ ] Faithfulness: __ / 2
- [ ] Coverage: __ / 2
- [ ] Boundary and uncertainty: __ / 2
- [ ] Actionability: __ / 2
- [ ] Abstention correctness: __ / 2 or N/A
- Reviewer: __
- Notes: __
""")
    return """# Human Review Queue

Status: **PENDING**. This file intentionally contains no invented human scores. Review each answer against the supplied source text; do not reward unsupported outside knowledge.

Scale: 0 = fails, 1 = partial, 2 = supported. A second reviewer is required before reporting agreement or a human quality score.

""" + '\n'.join(blocks)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', type=Path, default=ROOT / 'evaluation' / 'answer-quality-v1.json')
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--json', type=Path, default=ROOT / 'frontend' / 'public' / 'demo' / 'answer-evaluation.json')
    parser.add_argument('--markdown', type=Path, default=ROOT / 'docs' / 'answer-quality-evaluation.md')
    parser.add_argument('--human-review', type=Path, default=ROOT / 'evaluation' / 'human-review-v1.md')
    parser.add_argument('--fail-on-gate', action='store_true')
    args = parser.parse_args()
    dataset = json.loads(args.dataset.read_text(encoding='utf-8'))
    run = json.loads(args.run.read_text(encoding='utf-8'))
    if run['datasetVersion'] != dataset['version']:
        parser.error('run and dataset versions do not match')
    report = evaluate(dataset, run)
    for path, content in ((args.json, json.dumps(report, ensure_ascii=False, indent=2) + '\n'),
                          (args.markdown, report_markdown(report)),
                          (args.human_review, review_markdown(dataset, run))):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
    print(json.dumps({'passed': report['automatedGatePassed'], 'metrics': report['metrics'],
                      'humanReviewStatus': report['humanReviewStatus']}, ensure_ascii=False))
    if args.fail_on_gate and not report['automatedGatePassed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
