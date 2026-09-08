<template>
  <div class="workspace">
    <button v-if="navOpen" class="nav-scrim" aria-label="关闭导航" @click="navOpen = false" />
    <aside class="side-nav" :class="{ open: navOpen }">
      <router-link to="/overview" class="brand" @click="navOpen = false">
        <span class="brand-symbol"><AppIcon name="activity" /></span>
        <span>VPN ANALYST<small>异常流量研判平台</small></span>
      </router-link>
      <span class="nav-caption">研判导航</span>
      <nav aria-label="主导航">
        <router-link v-for="item in navigation" :key="item.path" :to="item.path" :aria-label="item.label"
          :class="{ active: activeSection === item.path }" @click="navOpen = false">
          <AppIcon :name="item.icon" /><span>{{ item.label }}</span>
          <span v-if="item.path === '/tasks' && activeCount" class="nav-counter">{{ activeCount }}</span>
        </router-link>
      </nav>
      <div class="nav-note"><span class="online-dot" />本地分析工作区<p>PCAP → 检测 → 证据 → 研判</p></div>
      <button class="nav-settings" @click="store.settingsOpen = true"><AppIcon name="settings" />连接与演示设置</button>
      <div class="nav-footer"><span class="avatar">L</span><div>本地分析员<small>开发演示环境 v1.0</small></div></div>
    </aside>

    <main class="workspace-main">
      <header class="workspace-topbar">
        <div class="breadcrumb"><button class="icon-button mobile-menu" aria-label="打开导航" @click="navOpen = true"><AppIcon name="menu" /></button>
          <span>工作区</span><AppIcon name="chevron" /><strong>{{ pageTitle }}</strong></div>
        <div class="topbar-actions">
          <span class="connection-status" :class="{ demo: store.demoMode }"><i />{{ route.path === '/knowledge' ? '资料与问答' : route.path === '/billing' ? '沙箱计费账户' : store.demoMode ? '离线演示 · 只读' : store.backendHealth?.status === 'UP' ? '后端已连接' : '等待服务连接' }}</span>
          <button class="icon-button" aria-label="连接设置" @click="store.settingsOpen = true"><AppIcon name="settings" /></button>
          <span class="topbar-divider" /><span class="avatar small">L</span>
        </div>
      </header>
      <div v-if="store.demoMode && !['/knowledge','/billing'].includes(route.path)" class="mode-banner"><AppIcon name="file" /><span>正在展示合成流量的离线分析产物。此模式不会上传文件或调用外部模型。</span><button @click="switchMode(false)">连接服务<AppIcon name="arrow" /></button></div>
      <div class="workspace-content">
        <div v-if="store.error" class="notice notice-warning"><AppIcon name="activity" /><span>{{ store.error }}</span><button @click="switchMode(true)">查看离线示例</button></div>
        <router-view :key="route.path + store.demoMode" />
      </div>
    </main>
    <CreateTaskDialog />
    <el-drawer v-model="store.settingsOpen" title="连接与演示设置" size="min(420px, 94vw)">
      <p class="muted">只读演示无需启动 Java、Python 或数据库。连接本地服务后可提交新样本。</p>
      <div class="settings-section"><h3>工作模式</h3>
        <el-radio-group :model-value="store.demoMode" @change="switchMode">
          <el-radio-button :value="false">连接后端</el-radio-button><el-radio-button :value="true">离线演示</el-radio-button>
        </el-radio-group>
      </div>
      <el-form label-position="top" @submit.prevent="saveConnection">
        <el-form-item label="Java API 地址"><el-input v-model="apiDraft" placeholder="http://127.0.0.1:8080" /></el-form-item>
        <el-button type="primary" :loading="store.loading" @click="saveConnection">保存并连接</el-button>
      </el-form>
      <p v-if="settingsError" class="error-text">{{ settingsError }}</p>
      <div class="settings-note"><AppIcon name="shield" /><p>当前平台用于本地开发与面试演示。离线数据不是在线告警，不代表模型检测效果。</p></div>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { usePlatformStore } from "./stores/platform";
import AppIcon from "./components/common/AppIcon.vue";
import CreateTaskDialog from "./components/workspace/CreateTaskDialog.vue";
const store = usePlatformStore(), route = useRoute(), router = useRouter();
const navOpen = ref(false), apiDraft = ref(store.apiBase), settingsError = ref("");
const navigation = [
  { path: "/overview", label: "工作台", icon: "grid" }, { path: "/tasks", label: "任务中心", icon: "tasks" },
  { path: "/reports", label: "研判报告", icon: "file" }, { path: "/knowledge", label: "知识检索", icon: "book" },
  { path: "/billing", label: "用量与计费", icon: "wallet" }
];
const activeSection = computed(() => route.path.startsWith("/tasks/") ? "/tasks" : route.path);
const pageTitle = computed(() => route.path.startsWith("/tasks/") ? "任务详情" : navigation.find(item => item.path === route.path)?.label || "工作台");
const activeCount = computed(() => (store.workbench?.statusCounts?.PROCESSING || 0) + (store.workbench?.statusCounts?.WAITING || 0));
async function switchMode(value) {
  const url = new URL(location.href);
  url.searchParams.delete("demo");
  history.replaceState(history.state, "", url);
  navOpen.value = false;
  await router.push("/overview");
  await store.changeMode(value);
}
async function saveConnection() {
  settingsError.value = "";
  try {
    const url = new URL(apiDraft.value);
    if (!["http:", "https:"].includes(url.protocol) || url.username || url.password) throw new Error();
    store.updateApiBase(url.href.replace(/\/$/, ""));
    await switchMode(false);
    if (!store.error) store.settingsOpen = false;
  } catch { settingsError.value = "请输入有效的 HTTP 或 HTTPS 服务地址。"; }
}
onMounted(async () => {
  if (new URLSearchParams(location.search).get("demo") === "1") await store.changeMode(true);
  else await store.initialize();
});
onUnmounted(() => store.clearDetail());
</script>
