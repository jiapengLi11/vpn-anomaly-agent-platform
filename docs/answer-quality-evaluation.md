# Answer Quality Development Baseline

This report evaluates a frozen model run with deterministic heuristics. It is not an independent benchmark, and automated PASS does not mean the prose is factually entailed by its citations.

- Dataset: `answer-quality-dev-v1`
- Run: `demo-extractive-20260908-v1`
- Provider/model: `demo / deterministic-extractive-v1`
- Answer mode: **EXTRACTIVE**
- Run status: **COMPLETE**
- Cases: 5 answered, 2 abstained
- Recorded tokens: 0
- Automated gate: **PASS**
- Human review: **PENDING**

> This run is a deterministic extractive baseline: the response copies retrieved source passages. Its 100% contract score validates the evaluation pipeline, citations, and abstention behavior; it is not a score for LLM generation quality.

## Automated Metrics

| Metric | Result | Gate | Status |
| --- | ---: | ---: | --- |
| statusSuccess | 100.00% | 100.00% | PASS |
| conceptCoverage | 100.00% | 80.00% | PASS |
| citationValidity | 100.00% | 100.00% | PASS |
| requiredSourceCoverage | 100.00% | 80.00% | PASS |
| forbiddenClaimAvoidance | 100.00% | 100.00% | PASS |
| abstentionAccuracy | 100.00% | 100.00% | PASS |

Concept coverage is keyword/synonym matching. Citation validity checks IDs, and required-source coverage checks cited sections. Neither proves semantic entailment.

## Case Diagnostics

| Case | Expected | Status | Missing concepts | Forbidden hits |
| --- | --- | --- | --- | --- |
| A01 | ANSWER | EXTRACTIVE | - | - |
| A02 | ANSWER | EXTRACTIVE | - | - |
| A03 | ANSWER | EXTRACTIVE | - | - |
| A04 | ANSWER | EXTRACTIVE | - | - |
| A05 | ANSWER | EXTRACTIVE | - | - |
| A06 | ABSTAIN | NO_SOURCES | - | - |
| A07 | ABSTAIN | NO_SOURCES | - | - |

An incomplete run can never pass the automated gate, even if its partial metrics happen to meet thresholds. The automated gate is suitable for regression only. Do not report it as RAG accuracy, faithfulness, or hallucination rate.
