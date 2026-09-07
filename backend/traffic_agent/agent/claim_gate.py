from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple


ALLOWED_TYPES = {"OBSERVATION", "INVESTIGATE", "LIMITATION"}
FORBIDDEN_TYPES = {"MALICIOUS", "BENIGN", "BLOCK", "ALLOW", "AUTO_REMEDIATE"}


def _evidence_registry(
    candidates: Iterable[Dict[str, Any]], knowledge_hits: Iterable[Dict[str, Any]]
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    evidence: Dict[str, Dict[str, Any]] = {}
    candidate_by_flow: Dict[str, Dict[str, Any]] = {}
    for candidate in candidates:
        flow_id = str(candidate.get("flowId") or candidate.get("flow_id") or "")
        if flow_id:
            candidate_by_flow[flow_id] = candidate
        for item in candidate.get("evidence", []) or []:
            if isinstance(item, dict) and item.get("id"):
                evidence[str(item["id"])] = {**item, "sourceType": "FLOW_EVIDENCE"}
    for hit in knowledge_hits:
        if isinstance(hit, dict) and hit.get("id"):
            evidence[str(hit["id"])] = {**hit, "sourceType": "KNOWLEDGE_EVIDENCE"}
    return evidence, candidate_by_flow


def validate_agent_claims(
    claims: Iterable[Dict[str, Any]],
    candidates: Iterable[Dict[str, Any]],
    knowledge_hits: Iterable[Dict[str, Any]],
) -> Dict[str, Any]:
    candidate_list = list(candidates)
    hit_list = list(knowledge_hits)
    registry, candidate_by_flow = _evidence_registry(candidate_list, hit_list)
    accepted: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []

    for index, raw_claim in enumerate(claims):
        claim = dict(raw_claim) if isinstance(raw_claim, dict) else {"text": str(raw_claim)}
        claim.setdefault("id", f"CLAIM-{index + 1:03d}")
        claim_type = str(claim.get("type") or "").upper()
        references = [str(item) for item in (claim.get("evidenceRefs") or []) if str(item)]
        unknown_refs = [item for item in references if item not in registry]

        reason = None
        if claim_type in FORBIDDEN_TYPES or claim_type not in ALLOWED_TYPES:
            reason = "UNSUPPORTED_CLAIM_TYPE"
        elif claim_type != "LIMITATION" and not references:
            reason = "MISSING_EVIDENCE_REFERENCES"
        elif unknown_refs:
            reason = "UNKNOWN_EVIDENCE_REFERENCE"
        elif claim_type == "INVESTIGATE":
            flow_id = str(claim.get("flowId") or "")
            candidate = candidate_by_flow.get(flow_id)
            if candidate is None or candidate.get("decision") != "CANDIDATE":
                reason = "FLOW_NOT_ADMITTED_AS_CANDIDATE"
            elif any(registry[item].get("flowId") != flow_id for item in references):
                reason = "WRONG_FLOW_EVIDENCE"
            elif not any(registry[item].get("strength") in {"STRONG", "MEDIUM"} for item in references):
                reason = "INSUFFICIENT_INVESTIGATION_EVIDENCE"

        audited = {
            **claim,
            "type": claim_type,
            "evidenceRefs": references,
            "validationStatus": "REJECTED" if reason else "ACCEPTED",
        }
        if reason:
            audited["rejectionReason"] = reason
            if unknown_refs:
                audited["unknownEvidenceRefs"] = unknown_refs
            rejected.append(audited)
        else:
            accepted.append(audited)

    return {
        "status": "PASSED" if not rejected else "PARTIAL" if accepted else "REJECTED",
        "scope": "STRUCTURED_CLAIMS_ONLY",
        "securityVerdict": "UNKNOWN",
        "acceptedClaims": accepted,
        "rejectedClaims": rejected,
        "acceptedCount": len(accepted),
        "rejectedCount": len(rejected),
        "availableEvidenceCount": len(registry),
        "narrativeValidationStatus": "UNVERIFIED_NARRATIVE",
    }
