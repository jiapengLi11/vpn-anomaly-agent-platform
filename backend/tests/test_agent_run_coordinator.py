import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from traffic_agent.agent.run_coordinator import AgentRunCoordinator
from traffic_agent.api import app


class AgentRunCoordinatorTest(unittest.TestCase):
    def test_knowledge_plan_runs_and_emits_ordered_events(self):
        coordinator = AgentRunCoordinator(tool_functions={
            "knowledge.search": lambda context: {"query": context["input"]["message"], "items": []}
        })
        preview = coordinator.preview("为什么 UDP 长连接值得关注？")
        self.assertEqual(preview["runPolicy"]["mode"], "LOCAL_READ_ONLY")
        run = coordinator.create_run("为什么 UDP 长连接值得关注？")
        completed = coordinator.execute(run["runId"])
        self.assertEqual(completed["status"], "SUCCESS")
        self.assertEqual([event["type"] for event in completed["events"]], [
            "PLAN_COMPILED", "RUN_STARTED", "STEP_STARTED", "STEP_COMPLETED", "RUN_FINISHED"])

    def test_pcap_plan_expands_three_tools_but_is_preview_only(self):
        preview = AgentRunCoordinator().preview(
            "分析这个 PCAP，检索可能的协议并生成研判报告。", context={"fileId": "demo-file"})
        self.assertEqual(preview["status"], "READY")
        self.assertEqual(preview["runPolicy"]["mode"], "PREVIEW_ONLY")
        self.assertEqual([step["tool"] for step in preview["plan"]["steps"]], [
            "knowledge.search", "protocol.hypothesize", "analyst.review"])

    def test_missing_file_clarifies_and_unknown_tool_fails_closed(self):
        coordinator = AgentRunCoordinator()
        missing = coordinator.preview("分析这个 PCAP 并生成报告")
        self.assertEqual(missing["status"], "CLARIFICATION_REQUIRED")
        rejected = coordinator.preview("为什么 UDP 长连接值得关注？",
                                       requested_tools=["shell.exec"])
        self.assertEqual(rejected["status"], "POLICY_REJECTED")
        self.assertEqual(rejected["compileError"]["code"], "UNKNOWN_TOOL")
        self.assertNotIn("shell.exec", json.dumps(rejected.get("plan")))

    def test_failure_is_degraded_without_exception_body(self):
        def fail(_context):
            raise RuntimeError("private upstream response")

        coordinator = AgentRunCoordinator(tool_functions={"knowledge.search": fail})
        run = coordinator.create_run("为什么 UDP 长连接值得关注？")
        completed = coordinator.execute(run["runId"])
        self.assertEqual(completed["status"], "DEGRADED")
        self.assertNotIn("private upstream response", json.dumps(completed))

    def test_run_store_is_bounded_and_routes_are_registered(self):
        coordinator = AgentRunCoordinator(max_runs=1)
        first = coordinator.create_run("为什么 UDP 长连接值得关注？")
        second = coordinator.create_run("为什么 TCP 长连接值得关注？")
        with self.assertRaises(KeyError):
            coordinator.get_run(first["runId"])
        self.assertEqual(coordinator.get_run(second["runId"])["runId"], second["runId"])
        paths = {route.path for route in app.routes}
        self.assertIn("/api/agent/plans/preview", paths)
        self.assertIn("/api/agent/runs/{run_id}/events", paths)


if __name__ == "__main__":
    unittest.main()
