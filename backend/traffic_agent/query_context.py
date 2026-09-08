"""Conservative, inspectable follow-up resolution, not LLM query rewriting."""
import json
import re
from pathlib import Path

POLICY = json.loads((Path(__file__).resolve().parents[2] / 'shared' / 'followup-policy.json').read_text(encoding='utf-8'))


def is_followup(text):
    normalized = re.sub(r'[\s，。！？、,.!?：:；;]', '', text).lower()
    candidates = [normalized] + [normalized[len(p):] for p in POLICY['prefixes'] if normalized.startswith(p)]
    return any(candidate in POLICY['phrases'] for candidate in candidates)


def resolve_query(question, history):
    question = question.strip()
    if not is_followup(question):
        return {'query': question, 'strategy': 'STANDALONE', 'policyVersion': POLICY['version']}
    for message in reversed(history[-8:]):
        if message['role'] == 'user' and message['content'].strip() and not is_followup(message['content']):
            anchor = message['content'].strip()[:500]
            return {'query': anchor + ' ' + question, 'strategy': 'FOLLOWUP_ANCHORED',
                    'anchor': anchor, 'policyVersion': POLICY['version']}
    return {'query': question, 'strategy': 'NEEDS_CONTEXT', 'policyVersion': POLICY['version']}
