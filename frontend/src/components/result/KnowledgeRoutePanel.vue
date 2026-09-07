<template>
  <el-card class="span-2" shadow="never">
    <template #header>
      <div class="card-title">知识增强路线</div>
    </template>

    <el-alert
      :title="panelTitle"
      :description="panelDescription"
      :type="alertType"
      :closable="false"
      class="route-alert"
    />

    <div class="summary-grid route-grid">
      <div class="summary-item">
        <span>任务模型</span>
        <strong>{{ displayModelType(task?.modelType) }}</strong>
      </div>
      <div class="summary-item">
        <span>检索策略</span>
        <strong>{{ displayKnowledgeStrategy(strategyName) }}</strong>
      </div>
      <div class="summary-item">
        <span>命中数量</span>
        <strong>{{ knowledgeHitCount }}</strong>
      </div>
      <div class="summary-item">
        <span>主要来源</span>
        <strong>{{ sourceFamily }}</strong>
      </div>
    </div>

    <div class="query-panel">
      <span>本次检索词</span>
      <code>{{ knowledgeQuery }}</code>
    </div>

    <el-space wrap class="route-tags">
      <el-tag
        v-for="tag in strategyTags"
        :key="tag"
        effect="plain"
        type="info"
      >
        {{ displayKnowledgeTag(tag) }}
      </el-tag>
    </el-space>

    <div v-if="knowledgeHits.length" class="hit-list">
      <div
        v-for="item in knowledgeHits.slice(0, 3)"
        :key="item.id || `${item.title}-${item.source}`"
        class="hit-item"
      >
        <div class="hit-head">
          <strong>{{ item.title }}</strong>
          <el-tag size="small" :type="item.strategy === 'enhancement_route' ? 'warning' : 'success'">
            {{ displayKnowledgeStrategy(item.strategy) }}
          </el-tag>
        </div>
        <div class="hit-source">{{ item.source }}</div>
        <p>{{ item.content }}</p>
      </div>
    </div>
    <el-empty v-else description="当前任务还没有知识命中结果。" />
  </el-card>
</template>

<script setup>
import { computed } from "vue";

import {
  displayKnowledgeSourceFamily,
  displayKnowledgeStrategy,
  displayKnowledgeTag,
  displayModelType
} from "../../utils/format";

const props = defineProps({
  task: {
    type: Object,
    default: null
  },
  preview: {
    type: Object,
    default: null
  }
});

const knowledgeHits = computed(() => props.preview?.report?.knowledgeHits || []);
const knowledgeStrategy = computed(() => props.preview?.report?.knowledgeStrategy || {});
const knowledgeQuery = computed(() => props.preview?.report?.knowledgeQuery || "暂无检索词");
const knowledgeHitCount = computed(() => {
  return props.preview?.summary?.knowledgeHitCount ?? knowledgeHits.value.length ?? 0;
});

const strategyName = computed(() => knowledgeStrategy.value.name || "default_route");
const strategyTags = computed(() => knowledgeStrategy.value.preferredTags || []);
const sourceFamily = computed(() => displayKnowledgeSourceFamily(knowledgeHits.value[0]?.source));

const alertType = computed(() => {
  return props.task?.modelType === "FEATURE_RULES" ? "info" : "warning";
});

const panelTitle = computed(() => {
  if (props.task?.modelType === "FEATURE_RULES") {
    return "当前任务正在使用 FEATURE_RULES 兼容检索路线";
  }
  return "当前任务正在使用 SEQUENCE_ENCODER 主路线知识增强";
});

const panelDescription = computed(() => {
  if (props.task?.modelType === "FEATURE_RULES") {
    return "当前结果主要命中特征工程、规则证据、PCAP 解析和历史平台沉淀文档，用于兼容历史结果与对照分析。";
  }
  return "当前结果会优先命中商用 VPN、多视图、开放集和增强实验文档，用于支撑 SEQUENCE_ENCODER 主路线的解释与报告生成。";
});
</script>

<style scoped>
.route-alert {
  margin-bottom: 16px;
}

.route-grid {
  margin-bottom: 16px;
}

.query-panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}

.query-panel span {
  color: #6b7280;
  font-size: 13px;
}

.query-panel code {
  display: block;
  padding: 12px 14px;
  border-radius: 12px;
  background: #f6f8fb;
  color: #1f2937;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.6;
}

.route-tags {
  margin-bottom: 16px;
}

.hit-list {
  display: grid;
  gap: 12px;
}

.hit-item {
  padding: 14px 16px;
  border: 1px solid #e5edf6;
  border-radius: 14px;
  background: linear-gradient(180deg, #fbfdff 0%, #f6f8fb 100%);
}

.hit-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 6px;
}

.hit-source {
  margin-bottom: 8px;
  color: #6b7280;
  font-size: 12px;
  word-break: break-all;
}

.hit-item p {
  margin: 0;
  color: #374151;
  line-height: 1.65;
}
</style>
