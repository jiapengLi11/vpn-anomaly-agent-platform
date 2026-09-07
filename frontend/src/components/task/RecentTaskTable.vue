<template>
  <el-card class="span-2" shadow="never">
    <template #header>
      <div class="card-title">最近任务</div>
    </template>

    <div class="table-tools table-tools-wide">
      <el-input v-model="keyword" placeholder="按任务 ID、模型、阶段搜索" clearable />
      <el-select v-model="statusFilter">
        <el-option label="全部状态" value="ALL" />
        <el-option label="等待中" value="WAITING" />
        <el-option label="处理中" value="PROCESSING" />
        <el-option label="成功" value="SUCCESS" />
        <el-option label="失败" value="FAILED" />
      </el-select>
      <el-select v-model="modelFilter">
        <el-option label="全部模型" value="ALL" />
        <el-option label="FEATURE_RULES" value="FEATURE_RULES" />
        <el-option label="SEQUENCE_ENCODER" value="SEQUENCE_ENCODER" />
      </el-select>
      <el-select v-model="sortBy">
        <el-option label="按创建时间倒序" value="created-desc" />
        <el-option label="按创建时间正序" value="created-asc" />
        <el-option label="按进度倒序" value="progress-desc" />
        <el-option label="按耗时倒序" value="elapsed-desc" />
      </el-select>
    </div>

    <div class="table-caption">当前显示 {{ filteredTasks.length }} 条任务</div>

    <el-table :data="filteredTasks" @row-click="selectTask">
      <el-table-column prop="taskId" label="任务 ID" min-width="180" />
      <el-table-column label="状态" min-width="100">
        <template #default="{ row }">{{ row.statusDisplay || row.status }}</template>
      </el-table-column>
      <el-table-column label="阶段" min-width="120">
        <template #default="{ row }">{{ row.stageDisplay || row.stage }}</template>
      </el-table-column>
      <el-table-column prop="progress" label="进度" min-width="90">
        <template #default="{ row }">{{ row.progress }}%</template>
      </el-table-column>
      <el-table-column prop="modelType" label="模型" min-width="120" />
      <el-table-column prop="elapsedDisplay" label="耗时" min-width="120" />
    </el-table>
  </el-card>
</template>

<script setup>
import { computed, ref } from "vue";

const props = defineProps({
  tasks: {
    type: Array,
    default: () => []
  }
});

const emit = defineEmits(["select"]);

const keyword = ref("");
const statusFilter = ref("ALL");
const modelFilter = ref("ALL");
const sortBy = ref("created-desc");

const filteredTasks = computed(() => {
  const items = props.tasks.filter((task) => {
    const text = [task.taskId, task.modelType, task.stageDisplay, task.stage, task.statusDisplay, task.status]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    const keywordMatched = !keyword.value || text.includes(keyword.value.toLowerCase());
    const statusMatched = statusFilter.value === "ALL" || task.status === statusFilter.value;
    const modelMatched = modelFilter.value === "ALL" || task.modelType === modelFilter.value;
    return keywordMatched && statusMatched && modelMatched;
  });

  return items.toSorted((left, right) => compareTasks(left, right, sortBy.value));
});

function compareTasks(left, right, rule) {
  switch (rule) {
    case "created-asc":
      return toTime(left.createdAt) - toTime(right.createdAt);
    case "progress-desc":
      return (right.progress || 0) - (left.progress || 0);
    case "elapsed-desc":
      return (right.elapsedSeconds || 0) - (left.elapsedSeconds || 0);
    case "created-desc":
    default:
      return toTime(right.createdAt) - toTime(left.createdAt);
  }
}

function toTime(value) {
  if (!value) return 0;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 0 : date.getTime();
}

function selectTask(row) {
  emit("select", row);
}
</script>
