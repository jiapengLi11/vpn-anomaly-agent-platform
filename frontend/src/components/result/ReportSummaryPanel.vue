<template>
  <div class="page-grid">
    <el-card shadow="never">
      <template #header>
        <div class="card-title">报告摘要</div>
      </template>
      <template v-if="preview?.report">
        <el-space wrap>
          <el-tag :type="preview.report.riskLevel === 'UNKNOWN' ? 'info' : 'danger'">{{ preview.report.riskLevelDisplay || preview.report.riskLevel }}</el-tag>
          <el-tag v-for="item in preview.report.evidence || []" :key="item">
            {{ displayRule(item) }}
          </el-tag>
        </el-space>
        <p class="card-note">{{ preview.report.conclusion }}</p>
        <p class="card-note">{{ preview.report.riskLevelDescription }}</p>
        <p class="card-note">{{ preview.report.riskOverview }}</p>
        <p class="card-note">{{ preview.report.riskScoreBandDescription }}</p>
      </template>
      <el-empty v-else description="先在任务中心选择一个成功任务" />
    </el-card>

    <el-card shadow="never">
      <template #header>
        <div class="card-title">产物下载</div>
      </template>
      <el-space v-if="preview?.artifacts?.length" wrap>
        <el-button
          v-for="artifact in preview.artifacts.filter((item) => item.exists)"
          :key="artifact.type"
          tag="a"
          :href="apiUrl(artifact.downloadPath)"
          target="_blank"
        >
          下载 {{ artifact.fileName }}
        </el-button>
      </el-space>
      <el-empty v-else description="暂无产物可下载" />
    </el-card>

    <el-card
      v-if="preview?.report?.llm || preview?.summary?.llmReportStatus"
      class="span-2"
      shadow="never"
    >
      <template #header>
        <div class="card-title">通义增强解读</div>
      </template>
      <div class="summary-grid">
        <div class="summary-item">
          <span>状态</span>
          <strong>{{ preview.report?.llm?.status || preview.summary?.llmReportStatus || "-" }}</strong>
        </div>
        <div class="summary-item">
          <span>模型路线</span>
          <strong>{{ displayModelType(task?.modelType || preview.modelType) }}</strong>
        </div>
        <div class="summary-item">
          <span>融合模式</span>
          <strong>{{ displayFusionMode(task?.fusionMode || preview.summary?.fusionMode) }}</strong>
        </div>
        <div class="summary-item">
          <span>知识命中</span>
          <strong>{{ preview.summary?.knowledgeHitCount ?? preview.report?.knowledgeHits?.length ?? 0 }}</strong>
        </div>
      </div>

      <el-alert v-if="preview.report?.llm?.claimValidationStatus === 'UNVERIFIED_NARRATIVE'"
        class="task-alert" type="warning" :closable="false"
        title="以下为 LLM 辅助解读，尚未经过逐条 Claim 语义校验，不作为自动处置依据。" />
      <p v-if="preview.report?.llm?.reason" class="card-note">{{ preview.report.llm.reason }}</p>

      <div class="summary-grid">
        <div class="summary-item">
          <span>提供方</span>
          <strong>{{ preview.report?.llm?.provider || "Configured LLM" }}</strong>
        </div>
        <div class="summary-item">
          <span>模型</span>
          <strong>{{ preview.report?.llm?.model || "-" }}</strong>
        </div>
        <div class="summary-item">
          <span>当前推理后端</span>
          <strong>{{ preview.summary?.modelEvidence?.actualModelBackend || preview.summary?.modelExecution?.actualModelBackend || "-" }}</strong>
        </div>
        <div class="summary-item">
          <span>证据输入</span>
          <strong>{{ fusionInputDescription }}</strong>
        </div>
      </div>

      <div
        v-if="preview.report?.knowledgeStrategy?.name || preview.report?.knowledgeQuery"
        class="summary-grid"
      >
        <div class="summary-item">
          <span>知识策略</span>
          <strong>{{ displayKnowledgeStrategy(preview.report?.knowledgeStrategy?.name) }}</strong>
        </div>
        <div class="summary-item span-3">
          <span>检索词</span>
          <strong>{{ preview.report?.knowledgeQuery || "-" }}</strong>
        </div>
      </div>

      <el-alert
        v-if="fusionUsesFallback"
        class="task-alert"
        type="warning"
        :closable="false"
        title="当前增强报告已参考 SEQUENCE_ENCODER 路线信息，但推理后端仍是兼容回退结果。"
      />

      <p v-if="preview.report?.llmNarrative" class="card-note">{{ preview.report.llmNarrative }}</p>
      <p v-if="preview.report?.llmRiskAssessment" class="card-note">{{ preview.report.llmRiskAssessment }}</p>

      <el-alert
        v-if="preview.report?.llm?.error"
        class="task-alert"
        type="warning"
        :closable="false"
        :title="preview.report.llm.error"
      />
    </el-card>

    <el-card v-if="preview?.report?.knowledgeHits?.length" class="span-2" shadow="never">
      <template #header>
        <div class="card-title">本次命中文档片段</div>
      </template>
      <div class="evidence-grid">
        <div
          v-for="item in preview.report.knowledgeHits"
          :key="item.id || `${item.title}-${item.source}`"
          class="evidence-item"
        >
          <h4>{{ item.title }}</h4>
          <span>来源：{{ item.source }}</span>
          <span v-if="item.tags?.length">标签：{{ item.tags.join(" / ") }}</span>
          <span v-if="item.strategy">策略：{{ displayKnowledgeStrategy(item.strategy) }}</span>
          <span v-if="item.score != null">匹配分：{{ item.score }}</span>
          <p>{{ item.content }}</p>
        </div>
      </div>
    </el-card>

    <el-card
      v-if="preview?.report?.modelVersion || preview?.report?.trainingDataset"
      class="span-2"
      shadow="never"
    >
      <template #header>
        <div class="card-title">增强模型报告占位</div>
      </template>
      <div class="summary-grid">
        <div class="summary-item">
          <span>modelVersion</span>
          <strong>{{ preview.report.modelVersion || "-" }}</strong>
        </div>
        <div class="summary-item">
          <span>trainingDataset</span>
          <strong>{{ preview.report.trainingDataset || "-" }}</strong>
        </div>
        <div class="summary-item">
          <span>comparisonToBaseline</span>
          <strong>{{ preview.report.comparisonToBaseline?.note || "-" }}</strong>
        </div>
        <div class="summary-item">
          <span>openSetMetrics</span>
          <strong>{{ preview.report.openSetMetrics?.note || "-" }}</strong>
        </div>
      </div>
    </el-card>

    <el-card class="span-2" shadow="never">
      <template #header>
        <div class="card-title">重点证据摘要</div>
      </template>
      <div v-if="preview?.report?.evidenceSummaryCards?.length" class="evidence-grid">
        <div
          v-for="card in preview.report.evidenceSummaryCards"
          :key="`${card.rule}-${card.title}`"
          class="evidence-item"
        >
          <h4>{{ displayRule(card.title || card.rule || "证据项") }}</h4>
          <p>{{ normalizeRuleText(card.description || "暂无说明") }}</p>
          <span v-if="card.topFlowId">代表流：{{ card.topFlowId }}</span>
          <span v-if="card.topRiskScore != null">风险分：{{ card.topRiskScore }}</span>
          <span v-if="card.distribution">分布：{{ formatDistribution(card.distribution) }}</span>
          <span v-if="card.labelMix">标签占比：{{ formatDistribution(card.labelMix) }}</span>
        </div>
      </div>
      <el-empty v-else description="暂无证据摘要卡片" />
    </el-card>

    <el-card shadow="never">
      <template #header>
        <div class="card-title">判断依据</div>
      </template>
      <el-empty v-if="!preview?.report?.reasoning?.length" description="暂无判断依据" />
      <ul v-else class="plain-list">
        <li v-for="item in preview.report.reasoning" :key="item">{{ normalizeRuleText(item) }}</li>
      </ul>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <div class="card-title">处置建议</div>
      </template>
      <el-empty v-if="!preview?.report?.suggestions?.length" description="暂无处置建议" />
      <ul v-else class="plain-list">
        <li v-for="item in preview.report.suggestions" :key="item">{{ normalizeRuleText(item) }}</li>
      </ul>
    </el-card>

    <el-card
      v-if="preview?.report?.llmAnalystFindings?.length || preview?.report?.llmSuggestedActions?.length"
      class="span-2"
      shadow="never"
    >
      <template #header>
        <div class="card-title">增强报告要点</div>
      </template>
      <div class="page-grid">
        <el-card shadow="never">
          <template #header>
            <div class="card-title">研判发现</div>
          </template>
          <ul class="plain-list">
            <li v-for="item in preview.report.llmAnalystFindings || []" :key="item">{{ item }}</li>
          </ul>
        </el-card>
        <el-card shadow="never">
          <template #header>
            <div class="card-title">建议动作</div>
          </template>
          <ul class="plain-list">
            <li v-for="item in preview.report.llmSuggestedActions || []" :key="item">{{ item }}</li>
          </ul>
        </el-card>
      </div>
    </el-card>

    <el-card class="span-2" shadow="never">
      <template #header>
        <div class="card-title">重点流说明</div>
      </template>
      <div v-if="preview?.report?.topFlowExplanations?.length" class="evidence-grid">
        <div v-for="item in preview.report.topFlowExplanations" :key="item.flowId" class="evidence-item">
          <h4>{{ item.flowId }}</h4>
          <span>风险分：{{ item.riskScore }}</span>
          <p>{{ normalizeRuleText(item.explanation) }}</p>
        </div>
      </div>
      <el-empty v-else description="暂无重点流说明" />
    </el-card>
  </div>
</template>

<script setup>
import { computed } from "vue";

import { apiUrl } from "../../services/api";
import {
  displayFusionMode,
  displayKnowledgeStrategy,
  displayModelType,
  displayRule,
  formatDistribution,
  normalizeRuleText
} from "../../utils/format";

const props = defineProps({
  preview: {
    type: Object,
    default: null
  },
  task: {
    type: Object,
    default: null
  }
});

const fusionInputDescription = computed(() => {
  const fusionMode = props.task?.fusionMode || props.preview?.summary?.fusionMode;
  if (fusionMode === "FEATURE_PLUS_SEQUENCE_ENCODER") {
    return "规则/特征证据 + SEQUENCE_ENCODER 路线结果";
  }
  return "规则/特征证据";
});

const fusionUsesFallback = computed(() => {
  const fusionMode = props.task?.fusionMode || props.preview?.summary?.fusionMode;
  const backend = props.preview?.summary?.modelEvidence?.actualModelBackend
    || props.preview?.summary?.modelExecution?.actualModelBackend;
  return fusionMode === "FEATURE_PLUS_SEQUENCE_ENCODER" && backend && backend !== "SEQUENCE_ENCODER";
});
</script>
