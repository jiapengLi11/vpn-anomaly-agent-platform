<template>
  <el-card class="span-2" shadow="never">
    <template #header>
      <div class="card-title">当前结果路线提示</div>
    </template>
    <el-alert
      :title="banner.title"
      :description="banner.description"
      :type="banner.type"
      :closable="false"
    />
    <div class="summary-grid route-summary">
      <div class="summary-item">
        <span>任务 ID</span>
        <strong>{{ task?.taskId || "未选择" }}</strong>
      </div>
      <div class="summary-item">
        <span>模型类型</span>
        <strong>{{ displayModelType(task?.modelType) }}</strong>
      </div>
      <div class="summary-item">
        <span>结果状态</span>
        <strong>{{ task?.statusDisplay || task?.status || "-" }}</strong>
      </div>
      <div class="summary-item">
        <span>当前表现</span>
        <strong>{{ banner.summary }}</strong>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { computed } from "vue";

import { displayModelType } from "../../utils/format";

const props = defineProps({
  preview: { type: Object, default: null },
  task: {
    type: Object,
    default: null
  }
});

const banner = computed(() => {
  const modelType = props.task?.modelType;
  const backend = props.preview?.summary?.modelExecution?.actualModelBackend;
  if (backend === "SEQUENCE_ENCODER_DEMO") {
    return {
      type: "warning",
      title: "当前使用 序列编码分类器 烟雾测试兼容模型",
      description: "主检查点与当前标签空间不兼容，已使用烟雾测试模型跑通推理。其分数只能作为演示参考，不代表正式检测效果，也不会单独触发候选。",
      summary: backend
    };
  }
  if (modelType === "FEATURE_RULES") {
    return {
      type: "info",
      title: "当前任务正在使用 FEATURE_RULES 兼容路线",
      description:
        "这条路线主要用于历史结果复用与同样本对照。平台主叙事已经切到 SEQUENCE_ENCODER，后续更建议补跑主路线任务。",
      summary: "兼容结果可用，适合作为主路线的对照参考"
    };
  }

  if (backend === "SEQUENCE_ENCODER_WITH_BASELINE_AUGMENT" || backend === "SEQUENCE_ENCODER") {
    return { type: "info", title: "当前任务已执行 序列编码分类器 推理",
      description: "模型预测仅作为检测信号，不等于协议真值或恶意结论，请结合候选证据和人工复核。", summary: backend };
  }
  return {
    type: "warning",
    title: "请求 序列编码分类器 路线，尚无已确认的主模型推理结果",
    description:
      "请求的模型路线不等于当前执行后端。当前可能未完成分析或已降级，请检查模型执行元数据。",
    summary: backend || "暂无后端记录"
  };
});
</script>
