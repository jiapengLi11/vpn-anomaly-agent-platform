<template>
  <el-card shadow="never">
    <template #header>
      <div class="card-title">结果摘要</div>
    </template>
    <template v-if="preview">
      <div class="hero-kpis">
        <div class="hero-kpi">
          <span>会话流总数</span>
          <strong>{{ preview.summary?.flowCount ?? "-" }}</strong>
        </div>
        <div class="hero-kpi">
          <span>{{ preview.summary?.candidateGate ? '历史启发式高分流' : '高风险流' }}</span>
          <strong>{{ preview.summary?.highRiskCount ?? "-" }}</strong>
        </div>
        <div class="hero-kpi">
          <span>疑似隧道流</span>
          <strong>{{ preview.summary?.encryptedTunnelCount ?? "-" }}</strong>
        </div>
        <div class="hero-kpi">
          <span>{{ preview.summary?.candidateGate ? '历史启发式最高分' : '最高风险分' }}</span>
          <strong>{{ preview.summary?.topRiskScore ?? "-" }}</strong>
        </div>
      </div>

      <p class="card-note">{{ preview.humanReadableSummary }}</p>

      <div class="chip-section">
        <div class="chip-block">
          <h4>协议分布</h4>
          <el-space wrap>
            <el-tag
              v-for="(value, key) in preview.summary?.protocolDistribution || {}"
              :key="key"
            >
              {{ key }}: {{ value }}
            </el-tag>
          </el-space>
        </div>
        <div class="chip-block">
          <h4>标签分布</h4>
          <el-space wrap>
            <el-tag
              v-for="(value, key) in preview.summary?.labelDistribution || {}"
              :key="key"
              type="success"
            >
              {{ key }}: {{ value }}
            </el-tag>
          </el-space>
        </div>
        <div class="chip-block">
          <h4>规则命中排行</h4>
          <el-space wrap>
            <el-tag
              v-for="item in preview.ruleHits || []"
              :key="item.rule"
              type="warning"
            >
              {{ displayRule(item.displayName || item.rule) }}: {{ item.count }}
            </el-tag>
          </el-space>
        </div>
      </div>
    </template>
    <el-empty v-else description="当前还没有可展示的结果。" />
  </el-card>
</template>

<script setup>
import { displayRule } from "../../utils/format";

defineProps({
  preview: {
    type: Object,
    default: null
  }
});
</script>
