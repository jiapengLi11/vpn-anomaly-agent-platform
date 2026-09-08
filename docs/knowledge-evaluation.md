# Knowledge Retrieval Development Baseline

This report is generated from a small self-authored development set. It prevents known regressions; it is not an independent product-quality benchmark and must not be quoted as production accuracy.

- Dataset: `knowledge-retrieval-dev-v1`
- Corpus: `public-knowledge-v1`
- Cases: 12 retrieval, 5 out-of-domain, 4 conversation, 21 citation-contract checks
- Overall gate: **PASS**

## Metrics

| Metric | Result | Regression gate | Status |
| --- | ---: | ---: | --- |
| hitAt1 | 91.67% | 80.00% | PASS |
| hitAt3 | 100.00% | 100.00% | PASS |
| mrr | 95.83% | 90.00% | PASS |
| outOfDomainRejection | 100.00% | 100.00% | PASS |
| conversationResolution | 100.00% | 100.00% | PASS |
| citationContract | 100.00% | 100.00% | PASS |

Hit@K and MRR use the first matching labelled section. Out-of-domain rejection requires zero BM25 hits. Conversation resolution requires the expected strategy, query and top-3 section. Citation contract checks reference existence only, not semantic entailment.

## Retrieval Ranks

| Case | First relevant rank | Top sections |
| --- | ---: | --- |
| R01 | 1 | UDP 会话与双向流量, 调查候选不是恶意结论, 引用与人工复核 |
| R02 | 1 | 调查候选不是恶意结论, UDP 会话与双向流量, 长会话与周期性 |
| R03 | 1 | 长会话与周期性, 引用与人工复核 |
| R04 | 1 | 长会话与周期性, 引用与人工复核, 调查候选不是恶意结论 |
| R05 | 1 | 序列分类与开放集拒识, 调查候选不是恶意结论 |
| R06 | 1 | 序列分类与开放集拒识, 调查候选不是恶意结论, UDP 会话与双向流量 |
| R07 | 1 | 知识检索和空结果, 序列分类与开放集拒识 |
| R08 | 1 | 知识检索和空结果 |
| R09 | 2 | UDP 会话与双向流量, 调查候选不是恶意结论, 序列分类与开放集拒识 |
| R10 | 1 | 调查候选不是恶意结论, 序列分类与开放集拒识, 引用与人工复核 |
| R11 | 1 | 引用与人工复核, 调查候选不是恶意结论, 知识检索和空结果 |
| R12 | 1 | 引用与人工复核, 序列分类与开放集拒识, 长会话与周期性 |

## Gate Failures

- None at the configured gates.

## Reproduce

```powershell
$env:PYTHONPATH="backend"
python tools/evaluate_knowledge.py --fail-on-gate
```

The dataset and thresholds are versioned in `evaluation/knowledge-retrieval-v1.json`. Any corpus or retrieval change should update the evidence and review failures before changing a gate.
