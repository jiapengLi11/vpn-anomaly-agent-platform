<template>
  <el-card shadow="never">
    <template #header>
      <div class="card-title">任务状态</div>
    </template>

    <div v-if="task" class="status-stack">
      <el-alert
        :title="`${task.statusDisplay || task.status} | ${task.stageDisplay || task.stage}`"
        :type="taskAlertType(task)"
        :closable="false"
      />

      <el-progress :percentage="task.progress || 0" :stroke-width="12" />

      <div class="timeline-list">
        <div
          v-for="item in timelineItems"
          :key="item.key"
          class="timeline-row"
          :class="item.state"
        >
          <div class="timeline-dot"></div>
          <div class="timeline-content">
            <strong>{{ item.label }}</strong>
            <span>{{ item.description }}</span>
          </div>
        </div>
      </div>

      <el-descriptions :column="1" border>
        <el-descriptions-item label="任务 ID">{{ task.taskId }}</el-descriptions-item>
        <el-descriptions-item label="模型路线">
          {{ displayModelType(task.modelType) }}
        </el-descriptions-item>
        <el-descriptions-item label="报告融合模式">
          {{ displayFusionMode(task.fusionMode) }}
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatDateTime(task.createdAt) }}</el-descriptions-item>
        <el-descriptions-item label="最近更新">{{ formatDateTime(task.updatedAt) }}</el-descriptions-item>
        <el-descriptions-item label="完成时间">{{ formatDateTime(task.completedAt) }}</el-descriptions-item>
        <el-descriptions-item label="累计耗时">{{ task.elapsedDisplay || "-" }}</el-descriptions-item>
        <el-descriptions-item label="阶段说明">{{ task.stageDescription || "-" }}</el-descriptions-item>
      </el-descriptions>

      <el-alert
        v-if="task.errorMessage"
        :title="task.errorMessage"
        type="error"
        :closable="false"
      />
    </div>

    <el-empty v-else description="当前还没有选中的任务。" />
  </el-card>
</template>

<script setup>
import { computed } from "vue";

import {
  TIMELINE_ORDER,
  displayFusionMode,
  displayModelType,
  formatDateTime,
  taskAlertType
} from "../../utils/format";

const props = defineProps({
  task: {
    type: Object,
    default: null
  }
});

const timelineItems = computed(() => {
  if (!props.task) return [];
  const currentIndex = TIMELINE_ORDER.findIndex((item) => item.key === props.task.stage);
  const failed = props.task.status === "FAILED" || props.task.stage === "FAILED";

  const items = TIMELINE_ORDER.map((item, index) => {
    let state = "";
    if (!failed && currentIndex > index) {
      state = "done";
    } else if (!failed && currentIndex === index) {
      state = "current";
    } else if (failed && currentIndex >= 0 && currentIndex > index) {
      state = "done";
    } else if (failed && currentIndex === index) {
      state = "failed";
    }
    return { ...item, state };
  });

  if (failed && !items.some((item) => item.key === "FAILED")) {
    items.push({
      key: "FAILED",
      label: "处理失败",
      description: props.task.stageDescription || "任务执行失败，需要查看错误信息定位原因。",
      state: "failed"
    });
  }
  return items;
});
</script>
