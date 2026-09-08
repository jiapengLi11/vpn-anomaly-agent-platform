"""Deterministic tool admission and routing for the investigation workflow."""
from __future__ import annotations

from typing import Any, Dict, Iterable

ROUTER_VERSION = 'tool-router-v1'
TOOL_ORDER = ('knowledge.search', 'analyst.review')
TOOL_CATALOG = {
    'knowledge.search': {
        'version': '1.0', 'kind': 'RETRIEVAL', 'external': False,
        'purpose': 'Retrieve compact background knowledge from admitted evidence codes.',
        'requires': [], 'maxCalls': 1,
    },
    'analyst.review': {
        'version': '1.0', 'kind': 'MODEL', 'external': True,
        'purpose': 'Generate a review brief from admitted evidence and retrieved knowledge.',
        'requires': ['knowledge.search'], 'maxCalls': 1,
    },
}


def public_catalog():
    return {'routerVersion': ROUTER_VERSION,
            'tools': [{'name': name, **TOOL_CATALOG[name]} for name in TOOL_ORDER]}


def _evidence_summary(context: Dict[str, Any]):
    evidence = [item for candidate in context.get('candidates', [])
                for item in candidate.get('evidence', []) if isinstance(item, dict)]
    labels = sorted({str(item.get('code') or item.get('family') or item.get('kind'))[:80]
                     for item in evidence if item.get('code') or item.get('family') or item.get('kind')})
    return {'candidateCount': len(context.get('candidates', [])), 'evidenceCount': len(evidence),
            'evidenceLabels': labels[:20],
            'featureEvidencePresent': bool(context.get('featureEvidence')),
            'modelEvidencePresent': bool(context.get('modelEvidence'))}


def route_tools(context: Dict[str, Any], requested_tools: Iterable[str] | None = None):
    summary = _evidence_summary(context)
    requested = list(dict.fromkeys(str(name)[:100] for name in (requested_tools or [])))[:8]
    if not summary['candidateCount']:
        return {'routerVersion': ROUTER_VERSION, 'status': 'SKIPPED_NO_CANDIDATES',
                'selectedTools': [], 'rejectedTools': [], 'inputSummary': summary}
    has_evidence = summary['evidenceCount'] > 0 or summary['featureEvidencePresent'] or summary['modelEvidencePresent']
    if not has_evidence:
        return {'routerVersion': ROUTER_VERSION, 'status': 'NEEDS_EVIDENCE', 'selectedTools': [],
                'rejectedTools': [{'name': name, 'reason': 'NO_ADMITTED_EVIDENCE'} for name in requested],
                'inputSummary': summary}

    candidates = list(TOOL_ORDER) if not requested else requested
    selected, rejected = [], []
    for name in candidates:
        spec = TOOL_CATALOG.get(name)
        if spec is None:
            rejected.append({'name': name, 'reason': 'TOOL_NOT_REGISTERED'})
            continue
        missing = [dependency for dependency in spec['requires'] if dependency not in selected]
        if missing:
            rejected.append({'name': name, 'reason': 'MISSING_DEPENDENCY', 'missing': missing})
            continue
        selected.append(name)
    # A partial plan must not call the model without the full evidence path.
    if 'analyst.review' not in selected:
        if selected:
            rejected.append({'name': 'analyst.review', 'reason': 'REQUIRED_TERMINAL_TOOL_NOT_REQUESTED'})
        selected = []
    return {'routerVersion': ROUTER_VERSION, 'status': 'READY' if selected else 'REJECTED',
            'selectedTools': [{'name': name, 'version': TOOL_CATALOG[name]['version'],
                               'reason': 'DEFAULT_EVIDENCE_PATH' if not requested else 'EXPLICIT_ALLOWED_REQUEST'}
                              for name in selected],
            'rejectedTools': rejected, 'inputSummary': summary}
