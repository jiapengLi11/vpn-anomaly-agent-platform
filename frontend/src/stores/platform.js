import { computed, ref } from "vue";
import { defineStore } from "pinia";
import { createTask, fetchHealth, fetchWorkbench, fetchTask, fetchTaskPreview, getApiBase, setApiBase, uploadPcap } from "../services/api";
import { isDemoMode, setDemoMode } from "../services/demo";

export const usePlatformStore = defineStore("platform", () => {
  const apiBase = ref(getApiBase()), demoMode = ref(isDemoMode());
  const backendHealth = ref(null), workbench = ref(null), currentTask = ref(null), currentPreview = ref(null);
  const loading = ref(false), detailLoading = ref(false), creatingTask = ref(false), error = ref(""), detailError = ref("");
  const uploadOpen = ref(false), settingsOpen = ref(false), lastMessage = ref("");
  const recentTasks = computed(() => workbench.value?.recentTasks || []);
  const latestTask = computed(() => recentTasks.value[0] || null);
  let detailVersion = 0, initVersion = 0, timer;
  async function initialize() {
    const version = ++initVersion;
    loading.value = true; error.value = "";
    try {
      const data = await fetchWorkbench();
      if (version !== initVersion) return;
      workbench.value = data;
      let health;
      try { health = await fetchHealth(); } catch { health = { status: "UNKNOWN" }; }
      if (version === initVersion) backendHealth.value = health;
    } catch (e) {
      if (version !== initVersion) return;
      workbench.value = null; backendHealth.value = { status: "DOWN" };
      error.value = demoMode.value ? e.message : "暂时无法连接后端。请检查服务地址，或切换到只读离线演示。";
    } finally { if (version === initVersion) loading.value = false; }
  }
  function stopPolling() { clearTimeout(timer); timer = null; }
  function clearDetail() { ++detailVersion; stopPolling(); currentTask.value = null; currentPreview.value = null; detailError.value = ""; }
  async function loadTask(id, quiet = false) {
    stopPolling();
    const version = ++detailVersion;
    if (!quiet) { currentTask.value = null; currentPreview.value = null; }
    detailLoading.value = !quiet; detailError.value = "";
    try {
      const task = await fetchTask(id);
      if (version !== detailVersion) return;
      const preview = task.status === "SUCCESS" ? await fetchTaskPreview(id) : null;
      if (version !== detailVersion) return;
      currentTask.value = task; currentPreview.value = preview;
      if (["WAITING", "PROCESSING"].includes(task.status)) timer = setTimeout(() => loadTask(id, true), 3000);
      else if (recentTasks.value.some(item => item.taskId === id && item.status !== task.status)) void initialize();
    } catch (e) {
      if (version === detailVersion) detailError.value = e.message || "任务读取失败，请重试。";
    } finally { if (version === detailVersion) detailLoading.value = false; }
  }
  async function createAnalysisTask(file, modelType, fusionMode, enableLlmReport = false) {
    creatingTask.value = true;
    try {
      lastMessage.value = "正在上传样本...";
      const fileInfo = await uploadPcap(file);
      lastMessage.value = "正在创建分析任务...";
      const task = await createTask({ fileId: fileInfo.fileId, analysisType: "VPN_PROXY_DETECTION", modelType,
        fusionMode, enableLlmReport, enableKnowledgeEnhance: enableLlmReport });
      uploadOpen.value = false;
      await initialize();
      return task;
    } finally { creatingTask.value = false; lastMessage.value = ""; }
  }
  async function changeMode(value) {
    clearDetail(); setDemoMode(value); demoMode.value = value; workbench.value = null;
    await initialize();
  }
  function updateApiBase(value) { apiBase.value = setApiBase(value); }
  return { apiBase, demoMode, backendHealth, workbench, currentTask, currentPreview, recentTasks, latestTask,
    loading, detailLoading, creatingTask, error, detailError, uploadOpen, settingsOpen, lastMessage,
    initialize, loadTask, clearDetail, stopPolling, createAnalysisTask, changeMode, updateApiBase };
});
