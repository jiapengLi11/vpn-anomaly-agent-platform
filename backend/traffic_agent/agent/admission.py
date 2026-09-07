from __future__ import annotations

import hashlib
import ipaddress
import re
from typing import Any, Dict, Iterable, List, Tuple


POLICY_VERSION = "security-admission-v1.0"
DEFAULT_CANDIDATE_LIMIT = 20
REMOVED_FIELDS = {
    "filepath",
    "file_path",
    "pcappath",
    "pcap_path",
    "storagepath",
    "storage_path",
    "absolutepath",
    "absolute_path",
}
DOMAIN_FIELDS = {"sni", "sni_values", "hostname", "host_name", "domain", "domains"}
IPV4_PATTERN = re.compile(r"(?<![0-9.])(?:\d{1,3}\.){3}\d{1,3}(?![0-9.])")
IPV6_PATTERN = re.compile(r"(?<![0-9A-Fa-f:])[0-9A-Fa-f]*:[0-9A-Fa-f:]+(?![0-9A-Fa-f:])")


def _alias(prefix: str, value: str, salt: str) -> str:
    digest = hashlib.sha256(f"{salt}:{value}".encode("utf-8")).hexdigest()[:8].upper()
    return f"{prefix}_{digest}"


def _replace_addresses(value: str, salt: str, aliases: Dict[str, str]) -> str:
    def replace(match: re.Match) -> str:
        candidate = match.group(0)
        try:
            ipaddress.ip_address(candidate)
        except ValueError:
            return candidate
        aliases.setdefault(candidate, _alias("HOST", candidate, salt))
        return aliases[candidate]

    value = IPV4_PATTERN.sub(replace, value)
    return IPV6_PATTERN.sub(replace, value)


def _redact_domain_value(value: Any, salt: str, domains: Dict[str, str]) -> Any:
    if isinstance(value, list):
        return [_redact_domain_value(item, salt, domains) for item in value]
    text = str(value or "").strip()
    if not text:
        return text
    parts = [part.strip() for part in re.split(r"[,;]", text) if part.strip()]
    redacted = []
    for part in parts:
        domains.setdefault(part, _alias("DOMAIN", part, salt))
        redacted.append(domains[part])
    return ",".join(redacted)


def _sanitize(
    value: Any,
    *,
    salt: str,
    address_aliases: Dict[str, str],
    domain_aliases: Dict[str, str],
    removed: List[str],
    parent_key: str = "",
) -> Any:
    if isinstance(value, dict):
        result: Dict[str, Any] = {}
        for key, item in value.items():
            normalized = str(key).lower()
            if normalized in REMOVED_FIELDS or normalized.endswith("path"):
                removed.append(str(key))
                continue
            if normalized in DOMAIN_FIELDS:
                result[str(key)] = _redact_domain_value(item, salt, domain_aliases)
                continue
            result[str(key)] = _sanitize(
                item,
                salt=salt,
                address_aliases=address_aliases,
                domain_aliases=domain_aliases,
                removed=removed,
                parent_key=normalized,
            )
        return result
    if isinstance(value, list):
        return [
            _sanitize(
                item,
                salt=salt,
                address_aliases=address_aliases,
                domain_aliases=domain_aliases,
                removed=removed,
                parent_key=parent_key,
            )
            for item in value
        ]
    if isinstance(value, tuple):
        return list(
            _sanitize(
                list(value),
                salt=salt,
                address_aliases=address_aliases,
                domain_aliases=domain_aliases,
                removed=removed,
                parent_key=parent_key,
            )
        )
    if isinstance(value, str):
        text = _replace_addresses(value, salt, address_aliases)
        return text[:1200]
    return value


def admit_agent_context(
    task_id: str,
    candidates: Iterable[Dict[str, Any]],
    *,
    feature_evidence: Dict[str, Any] | None = None,
    model_evidence: Dict[str, Any] | None = None,
    report_snapshot: Dict[str, Any] | None = None,
    candidate_limit: int = DEFAULT_CANDIDATE_LIMIT,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    if candidate_limit < 1 or candidate_limit > 50:
        raise ValueError("candidate_limit must be between 1 and 50")

    selected = list(candidates)
    admitted = selected[:candidate_limit]
    addresses: Dict[str, str] = {}
    domains: Dict[str, str] = {}
    removed: List[str] = []
    salt = task_id or "anonymous-task"
    context = _sanitize(
        {
            "taskId": task_id,
            "candidates": admitted,
            "featureEvidence": feature_evidence or {},
            "modelEvidence": model_evidence or {},
            "reportSnapshot": report_snapshot or {},
        },
        salt=salt,
        address_aliases=addresses,
        domain_aliases=domains,
        removed=removed,
    )
    admission = {
        "policyVersion": POLICY_VERSION,
        "status": "ADMITTED" if admitted else "SKIPPED_NO_CANDIDATES",
        "inputCandidateCount": len(selected),
        "admittedCandidateCount": len(admitted),
        "deferredCandidateCount": max(len(selected) - len(admitted), 0),
        "redactedAddressCount": len(addresses),
        "redactedDomainCount": len(domains),
        "removedFieldCount": len(removed),
        "removedFields": sorted(set(removed)),
        "rawPcapIncluded": False,
    }
    return context, admission


def sanitize_agent_data(task_id: str, value: Any) -> Any:
    """Apply the admission redaction policy to data added by downstream tools."""
    return _sanitize(
        value,
        salt=task_id or "anonymous-task",
        address_aliases={},
        domain_aliases={},
        removed=[],
    )
