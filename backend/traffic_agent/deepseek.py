from __future__ import annotations

import json
import os
import time
from pathlib import Path

import httpx
from pydantic import BaseModel, Field

SKILL = Path(__file__).with_name("skills") / "traffic-evidence-review" / "SKILL.md"


class Claim(BaseModel):
    type: str
    flowId: str = ""
    text: str = Field(max_length=1200)
    evidenceRefs: list[str] = Field(default_factory=list, max_length=20)


class Brief(BaseModel):
    narrative: str = Field(min_length=1, max_length=6000)
    applicability: list[str] = Field(default_factory=list, max_length=12)
    missingEvidence: list[str] = Field(default_factory=list, max_length=12)
    nextChecks: list[str] = Field(default_factory=list, max_length=12)
    claims: list[Claim] = Field(max_length=12)


def configuration():
    return {"provider": "deepseek", "configured": bool(os.getenv("DS_API_KEY") or os.getenv("DEEPSEEK_API_KEY")),
            "model": os.getenv("DS_MODEL") or os.getenv("DEEPSEEK_MODEL") or "deepseek-v4-flash", "skill": "traffic-evidence-review"}


def complete(context, schema=Brief, skill=SKILL):
    config = configuration()
    if not config["configured"]:
        return {**config, "status": "SKIPPED", "reason": "Set DS_API_KEY on the server", "claims": []}
    started = time.monotonic()
    try:
        prompt = skill.read_text(encoding="utf-8").split("---", 2)[-1].strip()
        response = httpx.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {os.getenv('DS_API_KEY') or os.environ['DEEPSEEK_API_KEY']}"},
            json={"model": config["model"], "response_format": {"type": "json_object"},
                  "max_tokens": 2200, "messages": [{"role": "system", "content": prompt},
                  {"role": "user", "content": json.dumps(context, ensure_ascii=False)}]},
            timeout=httpx.Timeout(60, connect=10), follow_redirects=False)
        response.raise_for_status()
        body = response.json()
        choice = body["choices"][0]
        if choice.get("finish_reason") != "stop":
            raise ValueError("Incomplete model output")
        brief = schema.model_validate_json(choice["message"]["content"])
        usage = {k: v for k, v in body.get("usage", {}).items()
                 if k in {"prompt_tokens", "completion_tokens", "total_tokens"} and isinstance(v, int)}
        return {**config, **brief.model_dump(), "skill": skill.parent.name, "status": "SUCCESS", "usage": usage,
                "elapsedMs": round((time.monotonic() - started) * 1000),
                "narrativeValidationStatus": "UNVERIFIED_NARRATIVE"}
    except httpx.HTTPStatusError as exc:
        return {**config, "status": "FAILED", "errorType": type(exc).__name__,
                "upstreamStatus": exc.response.status_code, "claims": [],
                "elapsedMs": round((time.monotonic() - started) * 1000)}
    except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
        return {**config, "status": "FAILED", "errorType": type(exc).__name__, "claims": [],
                "elapsedMs": round((time.monotonic() - started) * 1000)}


def analyze(context):
    return complete(context)
