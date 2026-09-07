<template>
  <div v-if="agent" class="agent-workspace">
    <section class="agent-hero panel">
      <div><span class="agent-kicker">AGENT EXECUTION TRACE</span><h2>证据驱动的研判编排</h2><p>模型只生成调查解释，结构化结论必须经过证据门禁；最终安全判定不会由 LLM 覆盖。</p></div>
      <div class="agent-verdict"><span>安全判定</span><strong>{{ agent.securityVerdict || "UNKNOWN" }}</strong><small>{{ agent.runtimeBackend }}</small></div>
    </section>
    <section class="agent-metrics">
      <article><span>准入候选</span><strong>{{ agent.admission?.admittedCandidateCount ?? 0 }}</strong><small>最多 20 条进入上下文</small></article>
      <article><span>知识片段</span><strong>{{ agent.knowledgeHits?.length ?? 0 }}</strong><small>{{ agent.knowledgeStrategy?.name || "未启用检索" }}</small></article>
      <article class="accepted"><span>通过 Claim</span><strong>{{ agent.claimAudit?.acceptedCount ?? 0 }}</strong><small>证据引用有效</small></article>
      <article class="rejected"><span>拦截 Claim</span><strong>{{ agent.claimAudit?.rejectedCount ?? 0 }}</strong><small>越权或证据不足</small></article>
    </section>
    <section class="panel agent-trace-card">
      <div class="panel-header"><div><span class="section-eyebrow">WORKFLOW</span><h2>节点执行轨迹</h2></div><span class="model-chip">{{ agent.workflowVersion }}</span></div>
      <div class="agent-trace">
        <article v-for="(step, index) in agent.trace || []" :key="step.sequence" :class="traceClass(step.status)">
          <div class="trace-index">{{ String(index + 1).padStart(2, "0") }}</div><div class="trace-line"><i /></div>
          <div class="trace-body"><div><strong>{{ nodeName(step.node) }}</strong><span>{{ step.status }}</span></div><p>{{ nodeDescription(step.node) }}</p><code>{{ detailText(step.details) }}</code></div>
        </article>
      </div>
    </section>
    <div class="report-columns agent-audit-grid">
      <section class="panel"><div class="panel-header"><h2>已接受结论</h2><span class="status-pill success"><i />GROUNDED</span></div><div v-if="!accepted.length" class="compact-empty"><p>当前没有通过证据校验的结构化结论。</p></div><article v-for="claim in accepted" :key="claim.id" class="claim-row accepted-claim"><span>{{ claim.type }}</span><h3>{{ claim.text }}</h3><p class="mono">{{ claim.flowId || "GLOBAL" }}</p><small>{{ claim.evidenceRefs?.length || 0 }} 个证据引用</small></article></section>
      <section class="panel"><div class="panel-header"><h2>已拦截结论</h2><span class="status-pill danger"><i />BLOCKED</span></div><div v-if="!rejected.length" class="compact-empty"><p>本次没有被门禁拦截的结构化结论。</p></div><article v-for="claim in rejected" :key="claim.id" class="claim-row rejected-claim"><span>{{ claim.type || "UNKNOWN" }}</span><h3>{{ claim.text }}</h3><p>{{ rejectionName(claim.rejectionReason) }}</p><small>{{ claim.id }}</small></article></section>
    </div>
    <section class="notice notice-warning agent-boundary"><strong>可审计边界</strong><span>自由文本仍标记为 {{ agent.claimAudit?.narrativeValidationStatus || "UNVERIFIED_NARRATIVE" }}；平台只对结构化 Claim 做证据引用校验，不执行自动封禁。</span></section>
  </div>
  <section v-else class="panel compact-empty agent-empty"><AppIcon name="activity" /><h2>本任务没有 Agent 执行记录</h2><p>新任务启用 LLM 辅助解读后，会在这里展示完整节点轨迹和 Claim 审计结果。</p></section>
</template>

<script setup>
import { computed } from "vue";
import AppIcon from "../common/AppIcon.vue";
const props = defineProps({ preview: Object });
const agent = computed(() => props.preview?.report?.agent || null);
const accepted = computed(() => agent.value?.claimAudit?.acceptedClaims || []);
const rejected = computed(() => agent.value?.claimAudit?.rejectedClaims || []);
const names = { security_admission: "安全准入", knowledge_retrieval: "知识检索", analyst_model: "分析模型", claim_gate: "结论门禁", finalize: "结果收敛" };
const descriptions = { security_admission: "限制候选规模并替换地址、域名与路径", knowledge_retrieval: "按模型与证据路由检索参考片段", analyst_model: "生成解释和带引用的结构化 Claim", claim_gate: "验证类型、会话和证据引用", finalize: "固定安全结论并封装审计产物" };
const reasons = { UNSUPPORTED_CLAIM_TYPE: "结论类型超出 Agent 授权范围", UNKNOWN_EVIDENCE_REFERENCE: "引用了不存在的证据", MISSING_EVIDENCE_REFERENCES: "缺少证据引用", FLOW_NOT_ADMITTED_AS_CANDIDATE: "目标会话未通过候选准入", WRONG_FLOW_EVIDENCE: "证据不属于目标会话", INSUFFICIENT_INVESTIGATION_EVIDENCE: "调查建议证据强度不足" };
const nodeName = value => names[value] || value;
const nodeDescription = value => descriptions[value] || "记录节点执行状态";
const rejectionName = value => reasons[value] || value || "未提供原因";
const traceClass = status => ({ success: ["SUCCESS", "PASSED", "ADMITTED"].includes(status), warning: ["PARTIAL", "DEGRADED"].includes(status), danger: ["FAILED", "REJECTED"].includes(status) });
function detailText(details = {}) { return Object.entries(details).map(([key, value]) => `${key}=${value}`).join(" · ") || "no extra metrics"; }
</script>
