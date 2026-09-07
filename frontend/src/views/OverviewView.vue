<template>
  <section class="page-enter">
    <div class="page-heading"><div><h1>分析工作台</h1><p>从流量样本到证据报告，专注每一次值得调查的通信。</p></div><el-button type="primary" size="large" @click="store.uploadOpen = true"><AppIcon name="plus" />新建分析</el-button></div>
    <div class="metric-grid" v-loading="store.loading">
      <div v-for="item in metrics" :key="item.label" class="metric-card"><div><span>{{ item.label }}</span><span class="metric-icon" :class="item.tone"><AppIcon :name="item.icon" /></span></div><strong>{{ item.value ?? '--' }}</strong><small>{{ item.hint }}</small></div>
    </div>
    <div class="overview-middle">
      <section class="latest-analysis">
        <div class="latest-decoration" aria-hidden="true"><span /><span /><span /></div>
        <div class="section-line"><span class="case-label">最近研判案卷</span><span class="outline-tag">{{ latestPreview ? '分析完成' : '等待样本' }}</span></div>
        <template v-if="latestPreview">
          <h2>最近一次研判</h2><p class="latest-file">{{ latestPreview.summary.fileName }}</p>
          <div class="analysis-flow"><div><strong>{{ latestPreview.summary.flowCount }}</strong><span>解析会话</span></div><div class="flow-divider" /><div class="focus"><strong>{{ gate?.candidateCount ?? '--' }}</strong><span>调查候选</span></div><div class="flow-divider" /><div><strong><AppIcon name="file" /></strong><span>证据报告</span></div></div>
          <div class="latest-bottom"><span><i />{{ backendName(latestPreview.summary.modelExecution?.actualModelBackend) }}</span><button @click="router.push('/tasks/' + latestPreview.taskId)">打开研判报告</button></div>
        </template>
        <template v-else><h2>让第一份样本<br />开启分析流程。</h2><p>上传 PCAP，查看会话特征、候选筛选与研判依据。</p><button class="hero-text-action" @click="store.uploadOpen = true">提交流量样本<AppIcon name="arrow" /></button></template>
      </section>
      <section class="panel workflow-panel"><div class="panel-header"><h2>分析流程</h2><span class="subtle-label">可追溯 · 可复核</span></div><ol class="workflow-steps"><li v-for="(step, i) in steps" :key="step.title"><span>{{ String(i + 1).padStart(2, '0') }}</span><div><strong>{{ step.title }}</strong><p>{{ step.text }}</p></div></li></ol><div class="workflow-foot"><AppIcon name="shield" />模型预测不等于恶意结论</div></section>
    </div>
    <section class="panel"><div class="panel-header"><div><h2>最近任务</h2><span class="subtle-label">最近创建的 6 条分析记录</span></div><router-link class="text-link link-icon" to="/tasks">全部任务<AppIcon name="arrow" /></router-link></div><TaskTable :items="store.recentTasks" /></section>
    <div class="page-footnote">统计范围：{{ store.demoMode ? '本次离线快照中的合成任务' : '本地工作区全部任务' }}，不是实时网络告警。</div>
  </section>
</template>
<script setup>
import { computed, ref, watch, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import { usePlatformStore } from "../stores/platform";
import { fetchTaskPreview } from "../services/api";
import { backendName } from "../utils/presentation";
import AppIcon from "../components/common/AppIcon.vue";
import TaskTable from "../components/workspace/TaskTable.vue";
const store = usePlatformStore(), router = useRouter(), latestPreview = ref(null);
let version = 0;
const gate = computed(() => latestPreview.value?.summary?.candidateGate);
const metrics = computed(() => [
  { label: "分析任务", value: store.workbench?.taskCount, icon: "tasks", hint: "工作区累计任务", tone: "" },
  { label: "处理中", value: store.workbench ? (store.workbench.statusCounts.PROCESSING || 0) + (store.workbench.statusCounts.WAITING || 0) : null, icon: "activity", hint: "分析中与等待中的任务", tone: "blue" },
  { label: "已完成", value: store.workbench?.statusCounts?.SUCCESS, icon: "check", hint: "可查看分析报告", tone: "green" },
  { label: "执行失败", value: store.workbench?.statusCounts?.FAILED, icon: "clock", hint: "需检查错误信息", tone: "amber" }
]);
const steps = [
  { title: "导入流量样本", text: "PCAP 解析与双向会话聚合" },
  { title: "识别调查候选", text: "特征、规则与模型分类信号" },
  { title: "查看证据与报告", text: "保留依据，交由分析员复核" }
];
watch(() => store.recentTasks, async tasks => {
  const id = ++version; latestPreview.value = null;
  const task = tasks.find(item => item.status === "SUCCESS");
  if (!task) return;
  try { const data = await fetchTaskPreview(task.taskId); if (id === version) latestPreview.value = data; } catch { /* Workbench remains usable when an artifact is unavailable. */ }
}, { immediate: true });
onUnmounted(() => ++version);
</script>
