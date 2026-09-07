<template>
  <el-table :data="items" class="task-table" :row-class-name="() => 'clickable-row'" @row-click="open">
    <el-table-column label="分析任务 / 样本" min-width="280"><template #default="{ row }"><div class="sample-cell"><span class="file-symbol"><AppIcon name="file" /></span><div><button class="text-link file-name" @click.stop="open(row)">{{ row.fileName || row.taskId }}</button><small class="mono">{{ row.taskId }}</small></div></div></template></el-table-column>
    <el-table-column label="分析方式" min-width="155"><template #default="{ row }"><span class="model-chip">{{ modeName(row.fusionMode) }}</span></template></el-table-column>
    <el-table-column label="状态" width="130"><template #default="{ row }"><StatusPill :status="row.status" /></template></el-table-column>
    <el-table-column label="创建时间" width="145"><template #default="{ row }"><span class="table-muted">{{ dateTime(row.createdAt) }}</span></template></el-table-column>
    <el-table-column label="" width="100" align="right"><template #default="{ row }"><button class="table-action" @click.stop="open(row)">{{ row.status === 'SUCCESS' ? '查看报告' : '查看任务' }}<AppIcon name="chevron" /></button></template></el-table-column>
    <template #empty><div class="table-empty"><AppIcon name="tasks" /><strong>{{ emptyText }}</strong><p>调整筛选条件，或创建一个新的分析任务。</p></div></template>
  </el-table>
</template>
<script setup>
import { useRouter } from "vue-router";
import AppIcon from "../common/AppIcon.vue";
import StatusPill from "../common/StatusPill.vue";
import { dateTime, modeName } from "../../utils/presentation";
defineProps({ items: { type: Array, default: () => [] }, emptyText: { type: String, default: '暂无分析任务' } });
const router = useRouter();
const open = row => router.push(`/tasks/${row.taskId}`);
</script>
