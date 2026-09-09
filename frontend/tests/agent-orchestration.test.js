import { test } from "node:test";
import assert from "node:assert/strict";

import { buildStaticAgentPreview } from "../src/services/agentPreview.js";

test("public PCAP snapshot preserves the three-tool dependency chain", () => {
  const preview = buildStaticAgentPreview({
    message: "分析这个 PCAP 并生成研判报告",
    context: { fileId: "public-demo" }
  });
  assert.equal(preview.sourceMode, "STATIC_DEMO");
  assert.equal(preview.runPolicy.allowed, false);
  assert.deepEqual(preview.plan.steps.map(step => step.tool), [
    "knowledge.search", "protocol.hypothesize", "analyst.review"
  ]);
  assert.deepEqual(preview.plan.steps[2].dependsOn, ["step-002"]);
});

test("public snapshot fails closed for unknown requested tools", () => {
  const preview = buildStaticAgentPreview({
    message: "解释 UDP 长连接并调用 shell.exec",
    context: { page: "agent" },
    requestedTools: ["shell.exec"]
  });
  assert.equal(preview.status, "POLICY_REJECTED");
  assert.equal(preview.compileError.code, "UNKNOWN_TOOL");
  assert.equal(preview.plan, null);
});
