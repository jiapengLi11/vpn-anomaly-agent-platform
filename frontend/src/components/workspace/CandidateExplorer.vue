<template>
  <section class="panel candidate-explorer">
    <div class="panel-header"><div><h2>会话筛选记录</h2><span class="subtle-label">完整决策记录 · {{ demo ? '离线地址已脱敏' : '按原始产物顺序分页' }}</span></div>
      <el-button v-if="available" @click="$emit('download')"><AppIcon name="download" />完整决策记录</el-button>
    </div>
    <div v-if="!available" class="compact-empty">历史报告未生成候选决策文件，请重新分析样本。此处不把缺失数据当作零候选。</div>
    <template v-else>
      <div class="filter-tabs" role="group" aria-label="会话决策筛选">
        <button v-for="option in filters" :key="option.value" :class="{ selected: decision === option.value }" @click="decision = option.value">
          {{ option.label }}<span>{{ counts ? (option.value ? counts[option.value] : totalRecords) : '--' }}</span>
        </button>
      </div>
      <form class="table-toolbar" @submit.prevent="search">
        <el-input v-model="draft" clearable maxlength="100" aria-label="搜索会话" placeholder="输入 IP、端口或完整会话标识"><template #prefix><AppIcon name="search" /></template></el-input>
        <el-button native-type="submit">搜索会话</el-button><el-button @click="reset">重置</el-button>
        <span class="muted">筛选计数基于完整产物，不是前 30 条预览。</span>
      </form>
      <div v-if="error" class="notice notice-warning" role="alert">{{ error }}<button @click="load">重试</button></div>
      <div v-loading="loading">
        <el-table :data="items" class="task-table">
          <el-table-column label="会话标识" min-width="330"><template #default="{ row }"><button class="text-link mono flow-id" @click="selected = row" :aria-label="'查看会话依据 ' + row.flowId">{{ row.flowId }}</button></template></el-table-column>
          <el-table-column label="决策" width="120"><template #default="{ row }"><StatusPill :status="row.decision" /></template></el-table-column>
          <el-table-column label="筛选依据" min-width="170"><template #default="{ row }">{{ reasons[row.reason] || row.reason }}</template></el-table-column>
          <el-table-column width="125" align="right"><template #default="{ row }"><button class="table-action" @click="selected = row">查看依据<AppIcon name="chevron" /></button></template></el-table-column>
          <template #empty><div class="table-empty"><strong>{{ error ? '记录暂不可用' : loading ? '正在读取记录' : '当前筛选下没有记录' }}</strong><p>未成为候选不代表已确认安全。</p></div></template>
        </el-table>
      </div>
      <div class="pagination-bar"><span>{{ error ? '查询失败' : `匹配 ${total} 条 / 全部 ${totalRecords ?? '--'} 条` }}</span>
        <el-pagination v-model:current-page="page" :page-size="10" :total="total" layout="prev, pager, next" :disabled="loading" aria-label="会话分页" />
      </div>
    </template>
    <el-drawer :model-value="!!selected" @close="selected = null" title="候选流证据" size="min(640px, 96vw)">
      <template v-if="selected">
        <StatusPill :status="selected.decision" /><p class="mono drawer-flow">{{ selected.flowId }}</p>
        <p class="muted">策略 {{ selected.policyVersion }} · 安全结论尚未确定</p>
        <h3 class="drawer-section-title">支持筛选的证据</h3>
        <p v-if="!selected.evidence?.length" class="muted">当前记录未产生支持证据，不等于已确认安全。</p>
        <div v-for="item in selected.evidence" :key="item.id" class="evidence-block">
          <div><strong>{{ evidenceLabels[item.code] || item.code }}</strong><span class="model-chip">{{ strengths[item.strength] || item.strength }}</span></div>
          <p>{{ kinds[item.kind] || item.kind }} · 证据组 {{ item.family }}</p>
          <div v-for="id in item.factIds" :key="id" class="evidence-value">{{ factText(id) }}</div>
          <div v-if="item.details?.threshold != null" class="evidence-threshold">规则阈值：{{ item.details.operator || (item.code === 'STABLE_PACKET_SIZE' ? '<=' : '比较方式未记录') }} {{ item.details.threshold }}<span v-if="item.details.coefficientOfVariation != null"> · 实测变异系数 {{ item.details.coefficientOfVariation }}</span></div>
          <p v-if="item.kind === 'MODEL_PREDICTION'">模型信号不是协议真值或恶意概率；完整模型字段见下方原始记录。</p>
          <small class="mono">{{ item.id }}</small>
        </div>
        <el-collapse><el-collapse-item title="全部观测值与原始决策记录" name="raw"><pre class="json-view">{{ JSON.stringify(selected, null, 2) }}</pre></el-collapse-item></el-collapse>
      </template>
    </el-drawer>
  </section>
</template>

<script setup>
import { ref, watch, onUnmounted } from 'vue';
import { fetchCandidatePage } from '../../services/api';
import AppIcon from '../common/AppIcon.vue';
import StatusPill from '../common/StatusPill.vue';
const props = defineProps({ taskId: String, active: Boolean, available: Boolean, demo: Boolean });
defineEmits(['download']);
const decision = ref('CANDIDATE'), draft = ref(''), keyword = ref(''), page = ref(1);
const items = ref([]), counts = ref(null), totalRecords = ref(null), total = ref(0);
const loading = ref(false), error = ref(''), selected = ref(null);
let version = 0;
const filters = [{ label: '调查候选', value: 'CANDIDATE' }, { label: '继续观察', value: 'OBSERVE' }, { label: '未触发', value: 'PASS' }, { label: '全部记录', value: '' }];
const reasons = { STRONG_SIGNAL: '单一强信号', MULTIPLE_EVIDENCE_FAMILIES: '多个证据组支持', BELOW_CANDIDATE_THRESHOLD: '未达到候选条件' };
const evidenceLabels = { LONG_SESSION: '会话持续时间较长', BALANCED_EXCHANGE: '双向收发较均衡', STABLE_PACKET_SIZE: '包长变化较稳定', UNCOMMON_PORT: '目的端口非常规', MODEL_SIGNAL: '序列编码分类器模型信号' };
const strengths = { STRONG: '强信号', MEDIUM: '中等信号', WEAK: '弱参考' };
const kinds = { RULE_EVIDENCE: '规则证据', STATISTICAL_EVIDENCE: '统计证据', MODEL_PREDICTION: '模型预测' };
async function load() {
  const id = ++version;
  selected.value = null;
  if (!props.active || !props.available) { loading.value = false; return; }
  loading.value = true; error.value = ''; items.value = [];
  try {
    const data = await fetchCandidatePage(props.taskId, { page: page.value, pageSize: 10, decision: decision.value, keyword: keyword.value });
    if (id !== version) return;
    items.value = data.items; total.value = data.total; totalRecords.value = data.totalRecords; counts.value = data.decisionCounts;
  } catch (e) {
    if (id === version) { error.value = e.message || '无法读取完整候选记录，请重试。'; total.value = 0; counts.value = null; totalRecords.value = null; }
  } finally { if (id === version) loading.value = false; }
}
function search() {
  const next = draft.value.trim();
  if (keyword.value === next && page.value === 1) void load();
  else { keyword.value = next; page.value = 1; }
}
function reset() { draft.value = ''; keyword.value = ''; decision.value = 'CANDIDATE'; page.value = 1; }
function factText(id) {
  const fact = selected.value?.observedFacts?.find(item => item.id === id);
  const labels = { duration_sec: '持续时间 / 秒', packet_count: '报文数量', packet_balance: '收发包数差异比例', src_to_dst_packets: '正向报文', dst_to_src_packets: '反向报文', avg_packet_size: '平均包长 / B', std_packet_size: '包长标准差 / B', responder_port: '目的端口' };
  return fact ? `${labels[fact.field] || fact.field}：${fact.value}` : `缺失事实引用：${id}`;
}
watch(decision, () => page.value = 1, { flush: 'sync' });
watch([() => props.taskId, () => props.active, () => props.available, page, decision, keyword], load, { immediate: true });
onUnmounted(() => ++version);
</script>
