<template>
  <el-card class="span-2" shadow="never">
    <template #header>
      <div class="card-title">候选筛选与证据追溯</div>
    </template>
    <el-empty v-if="!gate" description="该任务尚无候选筛选记录，请使用新版本重新分析样本。" />
    <template v-else>
      <el-alert type="info" :closable="false"
        title="候选代表值得调查，不代表恶意；未进入候选也不代表确认安全。当前阈值为演示策略，未经标注集校准。" />
      <div class="hero-kpis candidate-counts">
        <div class="hero-kpi"><span>会话总数</span><strong>{{ gate.totalFlowCount }}</strong></div>
        <div class="hero-kpi"><span>调查候选</span><strong>{{ gate.candidateCount }}</strong></div>
        <div class="hero-kpi"><span>继续观察</span><strong>{{ gate.observeCount }}</strong></div>
        <div class="hero-kpi"><span>未触发候选</span><strong>{{ gate.passCount }}</strong></div>
      </div>
      <p class="card-note">
        策略：{{ gate.policyVersion }} · 候选占比 {{ (gate.candidateRatio * 100).toFixed(1) }}%
        · 安全判定：待人工复核。最多预览 30 条，完整依据可下载 candidate_decisions.json。
      </p>
      <p v-if="preview.summary?.llmCandidateInputCount != null" class="card-note">
        本次 LLM 输入 {{ preview.summary.llmCandidateInputCount }} 条候选；
        未纳入本批 {{ preview.summary.llmCandidateDeferredCount ?? 0 }} 条（不会自动补跑）。
      </p>
      <el-table :data="decisions" row-key="flowId" stripe>
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="decision-detail">
              <p>模型证据：{{ row.modelEvidence?.backend || '不可用' }} / {{ row.modelEvidence?.confidenceLevel }}</p>
              <p>校验范围：仅核对“建议调查”这一结构化结论及其证据，不代表已校验 LLM 自由文本。</p>
              <el-table :data="row.evidence" size="small">
                <el-table-column prop="code" label="证据规则" min-width="160" />
                <el-table-column prop="kind" label="证据类型" min-width="170" />
                <el-table-column prop="family" label="分组（同组不重复计票）" min-width="185" />
                <el-table-column prop="strength" label="策略等级" width="100" />
                <el-table-column prop="id" label="证据 ID" min-width="230" />
              </el-table>
              <details>
                <summary>查看观测值、阈值与能力边界</summary>
                <pre>{{ JSON.stringify(row, null, 2) }}</pre>
              </details>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="flowId" label="会话" min-width="260" />
        <el-table-column label="候选决策" width="125">
          <template #default="{ row }">
            <el-tag :type="row.decision === 'CANDIDATE' ? 'warning' : 'info'">{{ labels[row.decision] || row.decision }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="依据" min-width="160">
          <template #default="{ row }">{{ reasons[row.reason] || row.reason }}</template>
        </el-table-column>
        <el-table-column label="引用校验" width="125">
          <template #default="{ row }">{{ row.claimCheck?.status === 'ACCEPTED' ? '证据支持调查' : '未生成结论' }}</template>
        </el-table-column>
      </el-table>
    </template>
  </el-card>
</template>

<script setup>
import { computed } from "vue";
const props = defineProps({ preview: { type: Object, default: null } });
const gate = computed(() => props.preview?.report?.candidateGate || props.preview?.summary?.candidateGate);
const decisions = computed(() => props.preview?.report?.candidateDecisionsPreview || []);
const labels = { CANDIDATE: "调查候选", OBSERVE: "继续观察", PASS: "未触发" };
const reasons = { STRONG_SIGNAL: "单一强信号", MULTIPLE_EVIDENCE_FAMILIES: "多个证据组支持", BELOW_CANDIDATE_THRESHOLD: "未达到候选条件" };
</script>

<style scoped>
.candidate-counts { margin-top: 16px; }
.decision-detail { padding: 16px; }
pre { max-height: 350px; overflow: auto; white-space: pre-wrap; overflow-wrap: anywhere; }
summary { margin-top: 12px; cursor: pointer; }
</style>
