<template>
  <el-dialog v-model="store.uploadOpen" title="新建流量分析" width="min(600px, 94vw)" :close-on-click-modal="!store.creatingTask" :show-close="!store.creatingTask" :close-on-press-escape="!store.creatingTask" @closed="reset">
    <p class="dialog-intro">上传一个 PCAP 样本，提取会话特征并生成可追溯的研判报告。</p>
    <el-alert v-if="store.demoMode" type="info" :closable="false" title="离线演示为只读模式。请先在连接设置中连接后端。" />
    <el-form label-position="top" :disabled="store.creatingTask || store.demoMode">
      <el-form-item label="01 / 流量样本">
        <el-upload ref="upload" class="sample-upload" drag accept=".pcap,.pcapng" :auto-upload="false" :show-file-list="false" :on-change="selectFile">
          <AppIcon name="upload" class="upload-icon" /><strong>{{ file?.name || '点击选择或拖入 PCAP 文件' }}</strong>
          <span>{{ file ? (file.size / 1024 / 1024).toFixed(2) + ' MB · 点击更换文件' : '支持 .pcap / .pcapng，最大 500 MB' }}</span>
        </el-upload>
      </el-form-item>
      <el-form-item label="02 / 分析方式">
        <el-radio-group v-model="mode" class="mode-options">
          <el-radio value="FEATURE_PLUS_SEQUENCE_ENCODER" border><strong>特征 + 序列编码分类器</strong><small>模型分类信号辅助调查，执行后端以报告为准</small></el-radio>
          <el-radio value="FEATURE_ONLY" border><strong>仅特征证据</strong><small>按规则与统计证据筛选，用于快速对照</small></el-radio>
        </el-radio-group>
      </el-form-item>
      <div class="switch-setting"><div><strong>LLM 辅助解读</strong><p>可选。开启后可能调用外部 API；当前先建议本地验证。</p></div><el-switch v-model="llm" aria-label="LLM 辅助解读" /></div>
      <el-alert v-if="llm" type="warning" :closable="false" title="仅上传有权限分析的脱敏样本。外部 API 可能产生费用，LLM 结论需人工复核。" />
    </el-form>
    <p v-if="error" class="error-text" role="alert">{{ error }}</p>
    <template #footer><span class="muted dialog-progress">{{ store.lastMessage }}</span><el-button :disabled="store.creatingTask" @click="store.uploadOpen = false">取消</el-button><el-button type="primary" :loading="store.creatingTask" :disabled="!file || store.demoMode" @click="submit">开始分析<AppIcon name="arrow" /></el-button></template>
  </el-dialog>
</template>
<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import { usePlatformStore } from "../../stores/platform";
import AppIcon from "../common/AppIcon.vue";
const store = usePlatformStore(), router = useRouter();
const file = ref(null), mode = ref("FEATURE_PLUS_SEQUENCE_ENCODER"), llm = ref(false), error = ref(""), upload = ref(null);
function reset() { file.value = null; llm.value = false; error.value = ""; upload.value?.clearFiles(); }
function selectFile(selected) {
  error.value = ""; file.value = null;
  if (!/\.(pcap|pcapng)$/i.test(selected.name)) error.value = "请选择 PCAP 或 PCAPNG 文件。";
  else if (!selected.size || selected.size > 500 * 1024 * 1024) error.value = "文件不能为空，且不能超过 500 MB。";
  else file.value = selected.raw;
}
async function submit() {
  if (!file.value || store.creatingTask || store.demoMode) return;
  error.value = "";
  try {
    const task = await store.createAnalysisTask(file.value, mode.value === "FEATURE_ONLY" ? "FEATURE_RULES" : "SEQUENCE_ENCODER", mode.value, llm.value);
    await router.push(`/tasks/${task.taskId}`);
  } catch (e) { error.value = e.message || "创建失败，请检查服务连接后重试。"; }
}
</script>
