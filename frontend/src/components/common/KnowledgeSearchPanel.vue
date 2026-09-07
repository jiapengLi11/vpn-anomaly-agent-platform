<template>
  <el-card class="span-2" shadow="never">
    <template #header>
      <div class="card-title">文档知识检索</div>
    </template>

    <div class="knowledge-toolbar">
      <el-input
        v-model="query"
        placeholder="输入关键词，例如：SEQUENCE_ENCODER、SNI、商用 VPN"
        @keyup.enter="runSearch"
      />
      <el-button type="primary" :loading="loading" @click="runSearch">检索</el-button>
    </div>

    <el-alert
      class="task-alert"
      type="info"
      :closable="false"
      :title="`检索后端：${backendLabel}。知识证据用于通义增强报告，不替代 序列编码分类器 分类结果。`"
    />

    <el-alert v-if="errorMessage" class="task-alert" type="error" :closable="false" :title="errorMessage" />
    <el-alert
      v-if="degraded"
      class="task-alert"
      type="warning"
      :closable="false"
      title="部分检索能力暂不可用，当前展示可用通道或本地知识的结果。"
    />

    <el-empty v-if="!items.length && !loading" description="先输入一个查询词试试" />

    <div v-else class="evidence-grid">
      <div v-for="item in items" :key="item.id" class="evidence-item">
        <h4>{{ item.title }}</h4>
        <span>来源：{{ item.source }}</span>
        <span v-if="item.tags?.length">标签：{{ item.tags.join(" / ") }}</span>
        <span v-if="item.retrievalChannels?.length">召回：{{ item.retrievalChannels.join(" + ") }}</span>
        <p>{{ item.content }}</p>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { ref } from "vue";

import { searchKnowledge } from "../../services/api";

const props = defineProps({
  initialQuery: {
    type: String,
    default: "SEQUENCE_ENCODER"
  },
  modelType: {
    type: String,
    default: ""
  }
});

const query = ref(props.initialQuery);
const loading = ref(false);
const items = ref([]);
const backendLabel = ref("检测中");
const errorMessage = ref("");
const degraded = ref(false);
let requestVersion = 0;

async function runSearch() {
  const version = ++requestVersion;
  errorMessage.value = "";
  degraded.value = false;
  if (!query.value.trim()) {
    items.value = [];
    loading.value = false;
    backendLabel.value = "未查询";
    return;
  }
  loading.value = true;
  try {
    const response = await searchKnowledge(query.value.trim(), 5, props.modelType || null);
    if (version !== requestVersion) return;
    items.value = response.items || [];
    backendLabel.value = response.knowledgeBackend || "local-jsonl";
    degraded.value = items.value.some(item => item.fallbackReason || item.retrievalWarnings?.length);
  } catch {
    if (version !== requestVersion) return;
    items.value = [];
    backendLabel.value = "不可用";
    errorMessage.value = "知识检索请求失败，请检查分析服务状态后重试。";
  } finally {
    if (version === requestVersion) loading.value = false;
  }
}

runSearch();
</script>

<style scoped>
.knowledge-toolbar {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 12px;
  margin-bottom: 16px;
}
</style>
