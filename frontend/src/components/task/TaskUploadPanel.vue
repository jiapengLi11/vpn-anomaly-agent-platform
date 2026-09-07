<template>
  <el-card shadow="never">
    <template #header>
      <div class="card-title">上传与创建任务</div>
    </template>

    <el-form label-position="top">
      <el-form-item label="PCAP 文件">
        <el-upload
          :auto-upload="false"
          :show-file-list="true"
          :limit="1"
          :on-change="onFileChange"
          :on-remove="onFileRemove"
        >
          <template #trigger>
            <el-button>选择文件</el-button>
          </template>
        </el-upload>
      </el-form-item>

      <el-form-item label="模型路线">
        <el-select v-model="localModelType">
          <el-option label="SEQUENCE_ENCODER（主路线）" value="SEQUENCE_ENCODER" />
          <el-option label="FEATURE_RULES（兼容对照）" value="FEATURE_RULES" />
        </el-select>
      </el-form-item>

      <el-form-item label="报告融合模式">
        <el-select v-model="localFusionMode">
          <el-option label="仅使用特征证据" value="FEATURE_ONLY" />
          <el-option
            v-if="localModelType === 'SEQUENCE_ENCODER'"
            label="特征证据 + SEQUENCE_ENCODER 结果"
            value="FEATURE_PLUS_SEQUENCE_ENCODER"
          />
        </el-select>
        <div class="form-tip">
          当前模式只影响通义增强报告如何组织证据，不会让 LLM 替代规则或模型做最终判定。
        </div>
      </el-form-item>

      <el-form-item label="通义增强">
        <div class="switch-block">
          <el-switch v-model="localEnableLlmReport" />
          <span class="switch-tip">
            {{ localEnableLlmReport ? "启用通义增强解读" : "仅使用规则化报告" }}
          </span>
        </div>
      </el-form-item>

      <el-button type="primary" :loading="creatingTask" @click="submitTask">
        上传并创建任务
      </el-button>

      <el-alert
        class="task-alert"
        :title="message || '等待任务创建'"
        type="info"
        :closable="false"
      />

      <el-alert
        v-if="localEnableLlmReport"
        class="task-alert"
        title="当前任务会在结构化规则报告基础上追加通义增强解读"
        type="success"
        :closable="false"
        description="LLM 失败不会影响主任务成功，平台会保留基础规则报告并额外记录增强状态。"
      />

      <el-alert
        v-if="localFusionMode === 'FEATURE_PLUS_SEQUENCE_ENCODER'"
        class="task-alert"
        title="当前会将特征证据与 SEQUENCE_ENCODER 路线结果一起送入通义"
        type="warning"
        :closable="false"
        description="现阶段 SEQUENCE_ENCODER 推理适配层仍在接入中，若后端返回的是兼容回退结果，报告会明确提示，不会虚构模型结论。"
      />

      <el-alert
        v-else
        class="task-alert"
        title="当前仅使用特征证据生成增强报告"
        type="info"
        :closable="false"
        description="适合做基线排查和历史兼容对照，增强报告会重点引用规则命中、统计特征和知识库片段。"
      />
    </el-form>
  </el-card>
</template>

<script setup>
import { ref, watch } from "vue";

const props = defineProps({
  modelType: {
    type: String,
    default: "SEQUENCE_ENCODER"
  },
  fusionMode: {
    type: String,
    default: "FEATURE_PLUS_SEQUENCE_ENCODER"
  },
  enableLlmReport: {
    type: Boolean,
    default: true
  },
  creatingTask: {
    type: Boolean,
    default: false
  },
  message: {
    type: String,
    default: ""
  }
});

const emit = defineEmits([
  "update:modelType",
  "update:fusionMode",
  "update:enableLlmReport",
  "submit"
]);

const localModelType = ref(props.modelType);
const localFusionMode = ref(props.fusionMode);
const localEnableLlmReport = ref(props.enableLlmReport);
const selectedFile = ref(null);

watch(
  () => props.modelType,
  (value) => {
    localModelType.value = value;
  }
);

watch(
  () => props.fusionMode,
  (value) => {
    localFusionMode.value = value;
  }
);

watch(
  () => props.enableLlmReport,
  (value) => {
    localEnableLlmReport.value = value;
  }
);

watch(localModelType, (value) => {
  if (value !== "SEQUENCE_ENCODER" && localFusionMode.value !== "FEATURE_ONLY") {
    localFusionMode.value = "FEATURE_ONLY";
  }
  if (value === "SEQUENCE_ENCODER" && !localFusionMode.value) {
    localFusionMode.value = "FEATURE_PLUS_SEQUENCE_ENCODER";
  }
  emit("update:modelType", value);
});

watch(localFusionMode, (value) => {
  emit("update:fusionMode", value);
});

watch(localEnableLlmReport, (value) => {
  emit("update:enableLlmReport", value);
});

function onFileChange(file) {
  selectedFile.value = file.raw;
}

function onFileRemove() {
  selectedFile.value = null;
}

function submitTask() {
  emit("submit", {
    file: selectedFile.value,
    modelType: localModelType.value,
    fusionMode: localFusionMode.value,
    enableLlmReport: localEnableLlmReport.value
  });
}
</script>

<style scoped>
.switch-block {
  display: flex;
  align-items: center;
  gap: 12px;
}

.switch-tip,
.form-tip {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.form-tip {
  margin-top: 8px;
  line-height: 1.6;
}
</style>
