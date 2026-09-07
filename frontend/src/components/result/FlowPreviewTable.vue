<template>
  <el-card class="span-2" shadow="never">
    <template #header>
      <div class="card-title">高风险流预览</div>
    </template>
    <el-table :data="preview?.topRiskFlows || []">
      <el-table-column prop="flowId" label="Flow ID" min-width="240" />
      <el-table-column prop="protocol" label="协议" min-width="80" />
      <el-table-column prop="predictedLabel" label="标签" min-width="120" />
      <el-table-column prop="riskScore" label="风险分" min-width="90" />
      <el-table-column label="命中特征" min-width="220">
        <template #default="{ row }">
          {{ (row.hitFeatures || []).map(displayRule).join(", ") }}
        </template>
      </el-table-column>
      <el-table-column label="说明" min-width="340">
        <template #default="{ row }">
          {{ normalizeRuleText(row.explanation) }}
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup>
import { displayRule, normalizeRuleText } from "../../utils/format";

defineProps({
  preview: {
    type: Object,
    default: null
  }
});
</script>
