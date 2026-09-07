<template>
  <el-card class="span-2" shadow="never">
    <template #header>
      <div class="card-title">结果图表视图</div>
    </template>
    <div v-if="preview?.summary" class="chart-grid">
      <div class="chart-card">
        <h4>协议分布</h4>
        <div v-if="protocolItems.length" class="bar-chart">
          <div v-for="item in protocolItems" :key="item.label" class="bar-row">
            <div class="bar-meta">
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
            </div>
            <div class="bar-track">
              <div class="bar-fill" :style="{ width: `${item.percent}%` }"></div>
            </div>
          </div>
        </div>
        <el-empty v-else description="暂无协议分布" />
      </div>

      <div class="chart-card">
        <h4>标签分布</h4>
        <div v-if="labelItems.length" class="bar-chart">
          <div v-for="item in labelItems" :key="item.label" class="bar-row">
            <div class="bar-meta">
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
            </div>
            <div class="bar-track">
              <div class="bar-fill success" :style="{ width: `${item.percent}%` }"></div>
            </div>
          </div>
        </div>
        <el-empty v-else description="暂无标签分布" />
      </div>

      <div class="chart-card span-2">
        <h4>规则命中排行</h4>
        <div v-if="ruleHitItems.length" class="bar-chart">
          <div v-for="item in ruleHitItems" :key="item.label" class="bar-row">
            <div class="bar-meta">
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
            </div>
            <div class="bar-track">
              <div class="bar-fill warning" :style="{ width: `${item.percent}%` }"></div>
            </div>
          </div>
        </div>
        <el-empty v-else description="暂无规则命中排行" />
      </div>
    </div>
    <el-empty v-else description="先在任务中心选择一个成功任务" />
  </el-card>
</template>

<script setup>
import { computed } from "vue";

import { displayRule } from "../../utils/format";

const props = defineProps({
  preview: {
    type: Object,
    default: null
  }
});

function toChartItems(source, formatter = (key) => key) {
  const entries = Object.entries(source || {});
  if (!entries.length) return [];
  const max = Math.max(...entries.map(([, value]) => Number(value) || 0), 1);
  return entries
    .map(([key, value]) => ({
      label: formatter(key),
      value,
      percent: Math.max(8, Math.round(((Number(value) || 0) / max) * 100))
    }))
    .sort((left, right) => Number(right.value) - Number(left.value));
}

const protocolItems = computed(() => toChartItems(props.preview?.summary?.protocolDistribution));
const labelItems = computed(() => toChartItems(props.preview?.summary?.labelDistribution));
const ruleHitItems = computed(() => {
  const items = props.preview?.ruleHits || [];
  if (!items.length) return [];
  const max = Math.max(...items.map((item) => Number(item.count) || 0), 1);
  return items.map((item) => ({
    label: displayRule(item.displayName || item.rule),
    value: item.count,
    percent: Math.max(8, Math.round(((Number(item.count) || 0) / max) * 100))
  }));
});
</script>
