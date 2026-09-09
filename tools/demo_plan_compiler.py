from __future__ import annotations

import json
import sys
import threading
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from traffic_agent.orchestration import DagExecutor, PlanCompiler


def demo_registry():
    common = {"version": "1.0", "readOnly": True, "idempotent": True,
              "sideEffect": "NONE", "requiredPermissions": ["analysis:run"],
              "supportedIntents": ["PCAP_INVESTIGATION"]}
    return {
        "traffic.parse": {**common, "requires": [], "failurePolicy": "FAIL",
                          "dependencyMode": "ALL_SUCCESS", "requiredPermissions": ["traffic:read"]},
        "traffic.classify": {**common, "requires": ["traffic.parse"], "failurePolicy": "DEGRADE",
                             "dependencyMode": "ALL_SUCCESS"},
        "traffic.features": {**common, "requires": ["traffic.parse"], "failurePolicy": "FAIL",
                             "dependencyMode": "ALL_SUCCESS"},
        "evidence.join": {**common, "requires": ["traffic.classify", "traffic.features"],
                          "failurePolicy": "FAIL", "dependencyMode": "ALL_DONE"},
        "report.generate": {**common, "requires": ["evidence.join"], "failurePolicy": "DEGRADE",
                            "dependencyMode": "ALL_SUCCESS", "idempotent": False,
                            "sideEffect": "EXTERNAL_BILLABLE", "requiredPermissions": ["ai:invoke"],
                            "concurrencyKey": "llm-provider"},
    }


def main() -> None:
    plan = PlanCompiler(demo_registry()).compile(
        intent="PCAP_INVESTIGATION",
        proposal=[{"name": "report.generate", "parallel": True, "dependsOn": []}],
        granted_permissions={"traffic:read", "analysis:run", "ai:invoke"},
    )
    barrier = threading.Barrier(2)

    def branch(value):
        def run(_context):
            barrier.wait(timeout=2)
            return value
        return run

    execution = DagExecutor(max_workers=2).execute(plan, {
        "traffic.parse": lambda _context: [{"flowId": "DEMO-FLOW-1"}],
        "traffic.classify": branch({"candidateLabel": "encrypted_tunnel_candidate"}),
        "traffic.features": branch({"evidenceFamilies": ["DURATION", "DIRECTION"]}),
        "evidence.join": lambda context: {
            "availableBranches": sum(value is not None for value in context["dependencies"].values()),
            "securityVerdict": "UNKNOWN",
        },
        "report.generate": lambda context: {
            "status": "DEMO_ONLY", "conclusion": "候选流需要人工复核。",
            "evidence": next(iter(context["dependencies"].values())),
        },
    })
    payload = {
        "scope": "LOCAL_CONTROL_PLANE_DEMO",
        "claims": [
            "Dependencies and stages come from the server registry.",
            "Synthetic classification and feature branches run concurrently.",
            "This is not a distributed scheduler or throughput benchmark.",
        ],
        "plan": plan, "execution": execution,
    }
    output = ROOT / "output" / "dag-plan-demo.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output), "status": execution["status"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
