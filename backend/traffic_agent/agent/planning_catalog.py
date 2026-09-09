"""Public, metadata-only catalog used by the natural-language planning demo."""

PLAN_TOOL_CATALOG = {
    "knowledge.search": {
        "version": "1.0", "requires": [], "failurePolicy": "DEGRADE",
        "dependencyMode": "ALL_DONE", "readOnly": True, "idempotent": True,
        "sideEffect": "NONE", "requiredPermissions": ["knowledge:read"],
        "concurrencyKey": None, "supportedIntents": ["KNOWLEDGE_QA", "PCAP_INVESTIGATION"],
        "purpose": "Retrieve bounded background evidence from public demo documents.",
    },
    "protocol.hypothesize": {
        "version": "1.0", "requires": ["knowledge.search"], "failurePolicy": "DEGRADE",
        "dependencyMode": "ALL_DONE", "readOnly": True, "idempotent": True,
        "sideEffect": "NONE", "requiredPermissions": ["analysis:review"],
        "concurrencyKey": None, "supportedIntents": ["PCAP_INVESTIGATION"],
        "purpose": "Build a bounded protocol-family hypothesis; metadata only in the public runner.",
    },
    "analyst.review": {
        "version": "1.0", "requires": ["protocol.hypothesize"], "failurePolicy": "DEGRADE",
        "dependencyMode": "ALL_DONE", "readOnly": True, "idempotent": False,
        "sideEffect": "EXTERNAL_BILLABLE", "requiredPermissions": ["ai:invoke"],
        "concurrencyKey": "llm-provider", "supportedIntents": ["PCAP_INVESTIGATION"],
        "purpose": "Generate an evidence-bounded analyst brief; not bound to this public runner.",
    },
}


def planning_candidates(intent):
    return [
        {"name": name, "version": spec["version"], "purpose": spec["purpose"]}
        for name, spec in PLAN_TOOL_CATALOG.items()
        if intent in spec["supportedIntents"]
    ]
