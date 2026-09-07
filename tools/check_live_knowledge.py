"""One explicitly invoked, paid API smoke test using only public sample documents."""
import argparse
import json
import os
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from traffic_agent.knowledge_answer import answer

parser = argparse.ArgumentParser()
parser.add_argument('--model', required=True)
args = parser.parse_args()
os.environ['DS_MODEL'] = args.model
result = answer('开放集拒识是什么意思？它和恶意流量有什么区别？', [], 'deepseek')
summary = {k: result.get(k) for k in ('status', 'provider', 'model', 'elapsedMs', 'usage', 'citationValidation', 'message')}
summary['paragraphCount'] = len(result.get('paragraphs', []))
summary['sourceCount'] = len(result.get('sources', []))
print(json.dumps(summary, ensure_ascii=False, indent=2))
if result['status'] != 'SUCCESS':
    raise SystemExit(1)
print(json.dumps(result['paragraphs'], ensure_ascii=False, indent=2))
