from __future__ import annotations

import sys
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from traffic_agent.agent.tool_router import TOOL_CATALOG
from traffic_agent.orchestration import DagExecutor, PlanCompilationError, PlanCompiler


def registry():
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


PERMISSIONS = {"traffic:read", "analysis:run", "ai:invoke"}


class PlanCompilerTest(unittest.TestCase):
    def test_dependencies_and_parallelism_are_registry_derived(self):
        plan = PlanCompiler(registry()).compile(
            intent="PCAP_INVESTIGATION",
            proposal=[{"name": "report.generate", "dependsOn": ["shell.exec"],
                       "parallel": True, "requiredPermissions": []}],
            granted_permissions=PERMISSIONS,
        )
        self.assertEqual([stage["executionMode"] for stage in plan["stages"]],
                         ["SERIAL", "PARALLEL", "SERIAL", "SERIAL"])
        self.assertEqual(len(plan["dependencyExpandedTools"]), 4)
        self.assertFalse(plan["audit"]["proposalMetadataTrusted"])
        self.assertEqual(plan["audit"]["ignoredProposalFields"][0]["fields"],
                         ["dependsOn", "parallel", "requiredPermissions"])

    def test_unknown_tool_and_missing_permissions_are_rejected(self):
        compiler = PlanCompiler(registry())
        with self.assertRaises(PlanCompilationError) as unknown:
            compiler.compile(intent="PCAP_INVESTIGATION", proposal=["shell.exec"],
                             granted_permissions=PERMISSIONS)
        self.assertEqual(unknown.exception.code, "UNKNOWN_TOOL")
        with self.assertRaises(PlanCompilationError) as denied:
            compiler.compile(intent="PCAP_INVESTIGATION", proposal=["report.generate"],
                             granted_permissions={"traffic:read"})
        self.assertEqual(denied.exception.code, "PERMISSION_DENIED")

    def test_cycle_and_plan_size_are_rejected(self):
        cyclic = registry()
        cyclic["traffic.parse"]["requires"] = ["report.generate"]
        with self.assertRaises(PlanCompilationError) as cycle:
            PlanCompiler(cyclic).compile(intent="PCAP_INVESTIGATION", proposal=["report.generate"],
                                         granted_permissions=PERMISSIONS)
        self.assertEqual(cycle.exception.code, "DEPENDENCY_CYCLE")
        with self.assertRaises(PlanCompilationError) as too_large:
            PlanCompiler(registry(), max_steps=3).compile(
                intent="PCAP_INVESTIGATION", proposal=["report.generate"],
                granted_permissions=PERMISSIONS)
        self.assertEqual(too_large.exception.code, "PLAN_TOO_LARGE")

    def test_side_effect_tools_are_serialized(self):
        constrained = {
            name: {"requires": [], "failurePolicy": "DEGRADE", "dependencyMode": "ALL_DONE",
                   "sideEffect": "EXTERNAL_BILLABLE", "requiredPermissions": ["ai:invoke"],
                   "supportedIntents": ["REPORT_EXPLAIN"], "concurrencyKey": "provider"}
            for name in ("llm.first", "llm.second")
        }
        plan = PlanCompiler(constrained).compile(
            intent="REPORT_EXPLAIN", proposal=list(constrained), granted_permissions={"ai:invoke"})
        self.assertEqual([stage["executionMode"] for stage in plan["stages"]], ["SERIAL", "SERIAL"])

    def test_public_agent_registry_compiles_from_terminal_tool(self):
        plan = PlanCompiler(TOOL_CATALOG).compile(
            intent="PCAP_INVESTIGATION", proposal=["analyst.review"],
            granted_permissions={"knowledge:read", "ai:invoke"})
        self.assertEqual([step["tool"] for step in plan["steps"]],
                         ["knowledge.search", "analyst.review"])


class DagExecutorTest(unittest.TestCase):
    def test_fanout_is_concurrent_and_join_receives_both_results(self):
        plan = PlanCompiler(registry()).compile(
            intent="PCAP_INVESTIGATION", proposal=["report.generate"],
            granted_permissions=PERMISSIONS)
        barrier = threading.Barrier(2)

        def branch(value):
            def run(_context):
                barrier.wait(timeout=2)
                return value
            return run

        result = DagExecutor(max_workers=2).execute(plan, {
            "traffic.parse": lambda context: context["input"]["flows"],
            "traffic.classify": branch({"label": "candidate"}),
            "traffic.features": branch({"longLived": True}),
            "evidence.join": lambda context: {"available": sum(
                value is not None for value in context["dependencies"].values())},
            "report.generate": lambda context: {"status": "review_required",
                                                  "evidence": next(iter(context["dependencies"].values()))},
        }, input_data={"flows": [{"flowId": "FLOW-1"}]})
        self.assertEqual(result["status"], "SUCCESS")
        self.assertNotIn("results", result["audit"]["stages"][1])

    def test_degraded_branch_all_done_join_continues(self):
        plan = PlanCompiler(registry()).compile(
            intent="PCAP_INVESTIGATION", proposal=["evidence.join"],
            granted_permissions=PERMISSIONS)

        def fail(_context):
            raise RuntimeError("private model response")

        result = DagExecutor(max_workers=2).execute(plan, {
            "traffic.parse": lambda _context: ["flow"], "traffic.classify": fail,
            "traffic.features": lambda _context: {"feature": True},
            "evidence.join": lambda context: {"available": sum(
                value is not None for value in context["dependencies"].values())},
        })
        join_step = next(step["stepId"] for step in plan["steps"] if step["tool"] == "evidence.join")
        self.assertEqual(result["status"], "DEGRADED")
        self.assertEqual(result["results"][join_step], {"available": 1})
        self.assertNotIn("private model response", str(result["audit"]))


if __name__ == "__main__":
    unittest.main()
