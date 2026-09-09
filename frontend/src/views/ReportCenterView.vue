<template>
  <section class="page-enter report-center-page">
    <div class="page-heading">
      <div>
        <h1>研判报告</h1>
        <p>集中阅读已完成分析的结论、调查候选与证据覆盖，不在这里管理排队任务。</p>
      </div>
      <el-button type="primary" size="large" @click="store.uploadOpen = true">
        <AppIcon name="plus" />新建分析
      </el-button>
    </div>

    <section class="report-register" aria-label="报告概况">
      <article><span>报告总数</span><strong>{{ total }}</strong><small>已完成并可复核</small></article>
      <article><span>本页调查候选</span><strong>{{ metrics.candidates }}</strong><small>仅代表需要进一步核查</small></article>
      <article><span>知识证据覆盖</span><strong>{{ metrics.knowledge }}/{{ records.length }}</strong><small>附带可追溯检索片段</small></article>
      <article><span>辅助解读</span><strong>{{ metrics.llm }}/{{ records.length }}</strong><small>生成后仍需人工复核</small></article>
    </section>

    <section class="panel report-toolbar-panel">
      <form class="table-toolbar" @submit.prevent="search">
        <el-input v-model="keyword" clearable placeholder="搜索报告编号或样本名称" aria-label="搜索报告">
          <template #prefix><AppIcon name="search" /></template>
        </el-input>
        <el-button native-type="submit">查询报告</el-button>
        <button class="icon-button refresh-table" type="button" aria-label="刷新报告列表" @click="load"><AppIcon name="refresh" /></button>
      </form>
    </section>

    <div v-if="error" class="notice notice-warning">{{ error }}<button @click="load">重试</button></div>

    <div v-loading="loading" class="report-reading-room">
      <section v-if="featured" class="report-featured">
        <div class="report-featured-copy">
          <div class="report-file-meta"><span>最近生成的研判简报</span><small>{{ dateTime(featured.task.completedAt || featured.task.createdAt) }}</small></div>
          <h2>{{ featured.task.fileName || featured.task.taskId }}</h2>
          <p>{{ conclusion(featured) }}</p>
          <div class="report-featured-facts">
            <span><b>{{ flowCount(featured) }}</b> 会话流</span>
            <span><b>{{ candidateCount(featured) }}</b> 调查候选</span>
            <span><b>{{ knowledgeCount(featured) }}</b> 知识来源</span>
          </div>
          <button class="report-open-primary" @click="open(featured.task.taskId)">阅读完整报告<AppIcon name="arrow" /></button>
        </div>
        <aside class="report-featured-verdict">
          <span>当前结论</span><strong>{{ verdict(featured) }}</strong>
          <p>系统只提供调查线索，不执行自动封禁。</p>
          <small class="mono">{{ featured.task.taskId }}</small>
        </aside>
      </section>

      <section v-if="records.length" class="report-archive">
        <header>
          <div><h2>报告档案</h2><p>按生成时间倒序排列，点击案卷继续查看候选流、证据和 Agent 轨迹。</p></div>
          <span>第 {{ page }} 页</span>
        </header>
        <div class="report-card-grid">
          <article v-for="record in records" :key="record.task.taskId" class="report-card" @click="open(record.task.taskId)">
            <header>
              <span :class="['report-state', { attention: candidateCount(record) > 0 }]"><i />{{ verdict(record) }}</span>
              <small>{{ dateTime(record.task.completedAt || record.task.createdAt) }}</small>
            </header>
            <h3>{{ record.task.fileName || record.task.taskId }}</h3>
            <p>{{ conclusion(record) }}</p>
            <dl>
              <div><dt>会话</dt><dd>{{ flowCount(record) }}</dd></div>
              <div><dt>候选</dt><dd>{{ candidateCount(record) }}</dd></div>
              <div><dt>知识</dt><dd>{{ knowledgeCount(record) }}</dd></div>
              <div><dt>解读</dt><dd>{{ llmLabel(record) }}</dd></div>
            </dl>
            <footer>
              <code>{{ record.task.taskId }}</code>
              <button class="text-link" @click.stop="open(record.task.taskId)">查看研判<AppIcon name="chevron" /></button>
            </footer>
          </article>
        </div>
      </section>

      <div v-else-if="!loading" class="report-empty">
        <AppIcon name="file" /><strong>还没有可阅读的研判报告</strong>
        <p>完成一项流量分析后，报告会自动进入这里；等待中和失败任务仍在任务中心管理。</p>
        <el-button type="primary" @click="store.uploadOpen = true">新建分析</el-button>
      </div>
    </div>

    <div v-if="total" class="pagination-bar">
      <span>共 {{ total }} 份报告</span>
      <el-pagination v-model:current-page="page" :page-size="PAGE_SIZE" :total="total" layout="prev, pager, next" @current-change="load" />
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRouter } from "vue-router";
import { fetchTaskPage, fetchTaskPreview } from "../services/api";
import { usePlatformStore } from "../stores/platform";
import { dateTime } from "../utils/presentation";
import AppIcon from "../components/common/AppIcon.vue";

const PAGE_SIZE = 8;
const store = usePlatformStore();
const router = useRouter();
const records = ref([]), total = ref(0), page = ref(1), keyword = ref("");
const loading = ref(false), error = ref("");
let version = 0;

const featured = computed(() => records.value[0] || null);
const metrics = computed(() => records.value.reduce((result, record) => {
  result.candidates += candidateCount(record);
  if (knowledgeCount(record) > 0) result.knowledge += 1;
  if (record.preview?.report?.llm?.status === "SUCCESS") result.llm += 1;
  return result;
}, { candidates: 0, knowledge: 0, llm: 0 }));

const candidateCount = record => Number(record.preview?.summary?.candidateGate?.candidateCount ?? record.preview?.report?.candidateGate?.candidateCount ?? 0);
const flowCount = record => Number(record.preview?.summary?.flowCount ?? 0);
const knowledgeCount = record => Number(record.preview?.report?.knowledgeHits?.length ?? record.preview?.summary?.knowledgeHitCount ?? 0);
const verdict = record => candidateCount(record) > 0 ? "待人工复核" : "未发现候选";

function conclusion(record) {
  if (!record.preview) return "报告摘要暂时不可用，进入详情可重新加载完整产物。";
  return record.preview.report?.conclusion || record.preview.humanReadableSummary || "分析已完成，等待分析员复核证据。";
}

function llmLabel(record) {
  const status = record.preview?.report?.llm?.status;
  if (status === "SUCCESS") return "已生成";
  if (status === "FAILED") return "生成失败";
  return "基础报告";
}

const open = taskId => router.push(`/reports/${taskId}`);

async function load() {
  const id = ++version;
  loading.value = true;
  error.value = "";
  try {
    const data = await fetchTaskPage({ page: page.value, pageSize: PAGE_SIZE, keyword: keyword.value.trim(), status: "SUCCESS" });
    const settled = await Promise.allSettled(data.items.map(task => fetchTaskPreview(task.taskId)));
    if (id !== version) return;
    records.value = data.items.map((task, index) => ({ task, preview: settled[index].status === "fulfilled" ? settled[index].value : null }));
    total.value = data.total;
  } catch (reason) {
    if (id !== version) return;
    records.value = [];
    total.value = 0;
    error.value = reason.message || "无法读取研判报告";
  } finally {
    if (id === version) loading.value = false;
  }
}

function search() { page.value = 1; load(); }
onMounted(load);
onUnmounted(() => ++version);
</script>

