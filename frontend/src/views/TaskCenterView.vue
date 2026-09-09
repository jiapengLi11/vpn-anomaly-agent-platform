<template>
  <section class="page-enter">
    <div class="page-heading"><div><h1>任务中心</h1><p>上传样本、追踪分析进度，所有任务集中管理。</p></div><el-button type="primary" size="large" @click="store.uploadOpen = true"><AppIcon name="plus" />新建分析</el-button></div>
    <section class="panel">
      <div class="filter-tabs" role="group" aria-label="按状态筛选"><button v-for="item in tabs" :key="item.value" :class="{ selected: status === item.value }" @click="status = item.value">{{ item.label }}<span>{{ item.count ?? '--' }}</span></button></div>
      <form class="table-toolbar" @submit.prevent="search"><el-input v-model="keyword" clearable placeholder="搜索任务 ID 或样本名称" aria-label="搜索任务"><template #prefix><AppIcon name="search" /></template></el-input><el-select v-model="model" placeholder="全部模型" aria-label="筛选模型" clearable><el-option label="序列编码分类器" value="SEQUENCE_ENCODER" /><el-option label="特征 / 兼容对照" value="FEATURE_RULES" /></el-select><el-button native-type="submit">查询</el-button><button class="icon-button refresh-table" type="button" aria-label="刷新任务列表" @click="load"><AppIcon name="refresh" /></button></form>
      <div v-if="error" class="notice notice-warning">{{ error }}<button @click="load">重试</button></div>
      <div v-loading="loading"><TaskTable :items="items" empty-text="没有匹配的分析任务" /></div>
      <div class="pagination-bar"><span>共 {{ total }} 条任务</span><el-pagination v-model:current-page="page" :page-size="10" :total="total" layout="prev, pager, next" @current-change="load" /></div>
    </section>
    <div class="list-tip"><AppIcon name="file" /><div><strong>不知道从哪里开始？</strong><p>点击右上角“新建分析”上传 PCAP，完成后进入研判报告继续复核。</p></div></div>
  </section>
</template>
<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { fetchTaskPage } from "../services/api";
import { usePlatformStore } from "../stores/platform";
import TaskTable from "../components/workspace/TaskTable.vue";
import AppIcon from "../components/common/AppIcon.vue";
const store = usePlatformStore();
const status = ref(""), model = ref(""), keyword = ref(""), page = ref(1);
const items = ref([]), total = ref(0), loading = ref(false), error = ref("");
let version = 0;
const tabs = computed(() => [
  { label: "全部任务", value: "", count: store.workbench?.taskCount },
  { label: "分析中", value: "PROCESSING", count: store.workbench?.statusCounts?.PROCESSING },
  { label: "等待中", value: "WAITING", count: store.workbench?.statusCounts?.WAITING },
  { label: "已完成", value: "SUCCESS", count: store.workbench?.statusCounts?.SUCCESS },
  { label: "执行失败", value: "FAILED", count: store.workbench?.statusCounts?.FAILED }
]);
async function load() {
  const id = ++version; loading.value = true; error.value = "";
  try { const data = await fetchTaskPage({ page: page.value, pageSize: 10, keyword: keyword.value.trim(), status: status.value, modelType: model.value });
    if (id === version) { items.value = data.items; total.value = data.total; }
  } catch (e) { if (id === version) { items.value = []; total.value = 0; error.value = e.message || "无法读取任务列表"; } }
  finally { if (id === version) loading.value = false; }
}
function search() { page.value = 1; load(); }
watch([status, model], search);
onMounted(load);
onUnmounted(() => ++version);
</script>
