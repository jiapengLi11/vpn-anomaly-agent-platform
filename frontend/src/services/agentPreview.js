export function buildStaticAgentPreview(payload) {
  const unsafe = payload.requestedTools?.length;
  const pcap = Boolean(payload.context?.fileId);
  const tools = pcap
    ? ["knowledge.search", "protocol.hypothesize", "analyst.review"]
    : ["knowledge.search"];
  const steps = tools.map((tool, index) => ({
    stepId: `step-${String(index + 1).padStart(3, "0")}`,
    tool,
    dependsOn: index ? [`step-${String(index).padStart(3, "0")}`] : [],
    failurePolicy: "DEGRADE",
    sideEffect: tool === "analyst.review" ? "EXTERNAL_BILLABLE" : "NONE"
  }));
  if (unsafe) return {
    status: "POLICY_REJECTED",
    sourceMode: "STATIC_DEMO",
    intent: {
      intent: "KNOWLEDGE_QA",
      confidenceBand: "MEDIUM",
      toolCandidates: [{ name: "knowledge.search" }]
    },
    plan: null,
    compileError: { code: "UNKNOWN_TOOL" },
    runPolicy: { allowed: false, mode: "STATIC_PREVIEW", reason: "UNKNOWN_TOOL" }
  };
  return {
    status: "READY",
    sourceMode: "STATIC_DEMO",
    intent: {
      intent: pcap ? "PCAP_INVESTIGATION" : "KNOWLEDGE_QA",
      confidenceBand: pcap ? "HIGH" : "MEDIUM",
      toolCandidates: tools.map(name => ({ name }))
    },
    plan: {
      status: "COMPILED",
      steps,
      stages: steps.map((step, index) => ({
        stageId: `stage-${String(index + 1).padStart(3, "0")}`,
        executionMode: "SERIAL",
        stepIds: [step.stepId]
      })),
      audit: {
        authority: "SERVER_TOOL_REGISTRY",
        proposalMetadataTrusted: false,
        parallelStageCount: 0
      }
    },
    runPolicy: {
      allowed: false,
      mode: "STATIC_PREVIEW",
      reason: "PUBLIC_SNAPSHOT_IS_READ_ONLY"
    }
  };
}
