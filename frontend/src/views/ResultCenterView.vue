<template>
  <section class="page-enter">
    <router-link :to="backPath" class="back-link"><AppIcon name="arrow" />{{ backLabel }}</router-link>
    <div class="page-heading detail-heading"><div><h1>{{ preview?.summary?.fileName || task?.fileName || '任务分析详情' }}</h1><p class="mono">案卷编号 {{ route.params.taskId }}</p></div><div class="heading-actions"><el-button :loading="store.detailLoading" @click="store.loadTask(route.params.taskId)"><AppIcon name="refresh" />刷新</el-button><el-button v-if="preview" type="primary" @click="download('report')"><AppIcon name="download" />下载报告</el-button></div></div>
    <div v-if="store.detailError" class="notice notice-warning" role="alert">{{ store.detailError }}<button @click="store.loadTask(route.params.taskId)">重新加载</button></div>
    <el-skeleton v-if="store.detailLoading" :rows="8" animated />
    <template v-else-if="task">
      <div class="detail-meta"><StatusPill :status="task.status" /><span>{{ modeName(task.fusionMode) }}</span><span><AppIcon name="clock" />{{ dateTime(task.createdAt) }}</span><span>耗时 {{ duration(task.elapsedSeconds) }}</span></div>
      <section v-if="!preview" class="panel progress-panel"><h2>{{ task.status === 'FAILED' ? '任务执行失败' : '正在处理流量样本' }}</h2><p>{{ task.errorMessage || task.stageDescription || '请等待分析服务完成，页面会自动刷新进度。' }}</p><el-progress :percentage="task.progress || 0" :status="task.status === 'FAILED' ? 'exception' : undefined" /><div class="stage-strip"><span v-for="(stage, index) in stages" :key="stage.key" :class="{ done: index <= currentStage }"><b>{{ index + 1 }}</b>{{ stage.label }}</span></div></section>
      <template v-else>
        <div class="detail-stats"><div><span>会话流</span><strong>{{ preview.summary?.flowCount ?? '--' }}<small>条</small></strong></div><div class="candidate-stat"><span>调查候选</span><strong>{{ gate?.candidateCount ?? '--' }}<small>条</small></strong></div><div><span>继续观察</span><strong>{{ gate?.observeCount ?? '--' }}<small>条</small></strong></div><div><span>安全判定</span><strong class="text-stat">待人工复核</strong></div></div>
        <el-tabs v-model="tab" class="report-tabs">
          <el-tab-pane label="研判概览" name="overview">
            <div class="report-columns">
              <div class="report-primary">
                <section class="panel verdict-panel"><div class="panel-header"><h2>研判结论</h2><span class="status-pill warning"><i />{{ gate ? 'UNKNOWN' : '历史兼容结果' }}</span></div><div class="verdict-body"><span class="verdict-icon"><AppIcon name="shield" /></span><div><h3>{{ !gate ? '请结合原始证据复核历史报告' : gate.candidateCount > 0 ? '发现调查线索，尚不能确认安全风险' : '本次未筛出调查候选，不能据此确认安全' }}</h3><p>{{ preview.report?.conclusion || preview.humanReadableSummary }}</p><small>候选筛选用于发现值得调查的通信，不等同于确认 VPN 协议或恶意行为。</small></div></div><button class="panel-inline-action" @click="tab = 'candidates'">查看候选流与筛选依据<AppIcon name="arrow" /></button></section>
                <section class="panel"><div class="panel-header"><h2>协议分布</h2><span class="subtle-label">基于本次解析结果</span></div><div class="protocol-bars"><div v-for="(count, protocol) in preview.summary?.protocolDistribution || {}" :key="protocol"><div><strong>{{ protocol }}</strong><span>{{ count }} 条 · {{ percent(count) }}%</span></div><div class="protocol-track"><i :style="{ width: percent(count) + '%' }" /></div></div></div></section>
                <section class="panel"><div class="panel-header"><h2>建议复核方向</h2></div><ol class="review-list"><li v-for="(suggestion, index) in preview.report?.suggestions || []" :key="index"><span>{{ String(index + 1).padStart(2, '0') }}</span>{{ suggestion }}</li></ol></section>
              </div>
              <aside class="report-secondary">
                <section class="panel"><div class="panel-header"><h2>分析上下文</h2></div><dl class="context-list"><div><dt>当前执行后端</dt><dd>{{ backendName(backend) }}</dd></div><div><dt>输入方式</dt><dd>{{ modeName(task.fusionMode) }}</dd></div><div><dt>筛选策略</dt><dd class="mono">{{ gate?.policyVersion || '旧版无候选策略' }}</dd></div><div><dt>LLM 解读</dt><dd>{{ llmStatus }}</dd></div></dl><div v-if="backend === 'SEQUENCE_ENCODER_DEMO'" class="inline-caution">当前为烟雾测试兼容模型，仅用于流程验证，不代表主模型检测效果。</div></section>
                <section class="panel evidence-entry"><AppIcon name="book" /><h3>每个判断，都应有据可查</h3><p>查看事实引用、模型边界和知识来源，而不是只看一个风险分数。</p><button class="text-link" @click="tab = 'evidence'">查看证据与模型</button></section>
              </aside>
            </div>
          </el-tab-pane>
          <el-tab-pane :label="'候选会话' + (gate ? ' (' + gate.candidateCount + ')' : '')" name="candidates">
            <CandidateExplorer :task-id="task.taskId" :active="tab === 'candidates'" :available="!!gate" :demo="store.demoMode" @download="download('candidate-decisions')" />
          </el-tab-pane>
          <el-tab-pane label="证据与模型" name="evidence">
            <div class="report-columns"><section class="panel"><div class="panel-header"><h2>模型执行边界</h2></div><dl class="context-list"><div><dt>当前执行后端</dt><dd>{{ backendName(backend) }}</dd></div><div><dt>执行说明</dt><dd>{{ preview.summary?.modelExecution?.note || '未提供模型执行说明' }}</dd></div><div><dt>证据角色</dt><dd>模型分类是预测信号，不等于协议真值，也不等于恶意概率。</dd></div><div><dt>校验范围</dt><dd>当前只核对“建议调查”结构化结论及其证据引用，尚未逐条校验 LLM 自由文本。</dd></div></dl></section><section class="panel"><div class="panel-header"><h2>知识证据</h2></div><div v-if="!preview.report?.knowledgeHits?.length" class="compact-empty"><AppIcon name="book" /><p>本次报告未附带知识检索片段。</p><router-link to="/knowledge" class="text-link">前往知识检索</router-link></div><article v-for="hit in preview.report?.knowledgeHits || []" :key="hit.id" class="evidence-snippet"><h3>{{ hit.title }}</h3><p>{{ hit.content }}</p><small>{{ hit.id }}</small></article></section></div>
          </el-tab-pane>
          <el-tab-pane label="Agent 轨迹" name="agent"><AgentTracePanel :preview="preview" /></el-tab-pane>
          <el-tab-pane label="报告与产物" name="artifacts">
            <section class="panel"><div class="panel-header"><h2>分析产物</h2></div><div class="artifact-grid"><button v-for="artifact in artifacts" :key="artifact.type" class="artifact-card" @click="download(artifact.type)"><AppIcon name="file" /><strong>{{ artifact.label }}</strong><span>{{ artifact.name }}</span><AppIcon name="download" /></button></div></section>
            <section class="panel narrative-panel"><div class="panel-header"><h2>LLM 辅助解读</h2><span class="model-chip">{{ llmStatus }}</span></div><div v-if="preview.report?.llmNarrative" class="narrative"><div class="notice notice-warning">以下解读尚未经过逐条 Claim 语义校验，不能作为自动处置依据。</div><p>{{ preview.report.llmNarrative }}</p></div><div v-else class="compact-empty"><p>{{ preview.report?.llm?.reason || '本次未生成 LLM 辅助解读，基础报告和证据记录仍可使用。' }}</p></div></section>
          </el-tab-pane>
        </el-tabs>
      </template>
    </template>
  </section>
</template>
<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRoute } from "vue-router";
import { usePlatformStore } from "../stores/platform";
import { apiUrl } from "../services/api";
import { dateTime, duration, modeName, backendName } from "../utils/presentation";
import { TIMELINE_ORDER } from "../utils/format";
import AppIcon from "../components/common/AppIcon.vue";
import StatusPill from "../components/common/StatusPill.vue";
import CandidateExplorer from "../components/workspace/CandidateExplorer.vue";
import AgentTracePanel from "../components/result/AgentTracePanel.vue";
const store = usePlatformStore(), route = useRoute();
const tab = ref("overview");
const fromReports = computed(() => route.path.startsWith("/reports/"));
const backPath = computed(() => fromReports.value ? "/reports" : "/tasks");
const backLabel = computed(() => fromReports.value ? "返回研判报告" : "返回任务中心");
const task = computed(() => store.currentTask), preview = computed(() => store.currentPreview);
const gate = computed(() => preview.value?.summary?.candidateGate);
const backend = computed(() => preview.value?.summary?.modelExecution?.actualModelBackend);
const stages = TIMELINE_ORDER.filter(item => !["DISPATCHING", "CREATED"].includes(item.key));
const currentStage = computed(() => stages.findIndex(item => item.key === task.value?.stage));
const llmStatus = computed(() => ({ DISABLED: "未启用", SUCCESS: "已生成 · 待复核", FAILED: "生成失败", SKIPPED: "未配置", SKIPPED_NO_CANDIDATES: "无候选，已跳过" })[preview.value?.report?.llm?.status] || "未生成");
const artifacts = computed(() => [
  { type: "report", label: "研判报告", name: "report.json" },
  { type: "summary", label: "分析摘要", name: "summary.json" },
  ...(preview.value?.report?.agent ? [{ type: "agent-trace", label: "Agent 执行审计", name: "agent_trace.json" }] : []),
  ...(gate.value ? [{ type: "candidate-decisions", label: "候选决策与依据", name: "candidate_decisions.json" }] : [])
]);
const percent = count => preview.value?.summary?.flowCount ? ((count / preview.value.summary.flowCount) * 100).toFixed(1) : "0.0";
function download(type) {
  if (!store.demoMode) { window.open(apiUrl("/api/tasks/" + task.value.taskId + "/artifacts/" + type), "_blank", "noopener"); return; }
  const value = type === "report" ? preview.value.report : type === "summary" ? preview.value.summary : type === "agent-trace" ? preview.value.report?.agent : preview.value.offlineDecisions;
  const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }));
  const anchor = document.createElement("a"); anchor.href = url; anchor.download = (artifacts.value.find(a => a.type === type)?.name || type + ".json"); anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}
onMounted(() => store.loadTask(route.params.taskId));
onUnmounted(() => store.clearDetail());
</script>
