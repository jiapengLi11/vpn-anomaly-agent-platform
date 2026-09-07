<template>
  <section class="page-enter">
    <div class="page-heading"><div><h1>知识检索</h1><p>查找协议资料、规则说明与公开参考文档，让研判有据可循。</p></div><span class="page-badge"><AppIcon name="book" />证据参考，不替代流量事实</span></div>
    <div class="knowledge-search panel"><div class="knowledge-mark"><AppIcon name="search" /></div><h2>你想查找哪类研判依据？</h2><p>使用协议名、流量特征或一个完整问题开始检索。</p><form @submit.prevent="search"><el-input v-model="query" clearable size="large" placeholder="例如：如何理解 序列编码分类器 的开放集拒识？" aria-label="知识检索问题" /><el-button type="primary" size="large" :loading="loading" :disabled="store.demoMode" native-type="submit">检索文档<AppIcon name="arrow" /></el-button></form><div class="suggested-queries"><span>试试这些</span><button v-for="q in suggestions" :key="q" @click="query = q; search()">{{ q }}</button></div></div>
    <div v-if="store.demoMode" class="notice notice-info"><AppIcon name="book" /><span>离线演示只包含合成分析报告，不模拟在线检索结果。连接后端即可检索配置的知识库。</span><button @click="store.settingsOpen = true">连接设置</button></div>
    <div v-if="error" class="notice notice-warning" role="alert">{{ error }}</div>
    <template v-if="searched && !error"><div class="result-count">检索到 {{ items.length }} 个文档片段<span>后端：{{ backend || '无结果' }}</span></div><el-empty v-if="!items.length" description="暂无匹配内容，请尝试更明确的协议名或特征。" /><article v-for="(item, index) in items" :key="item.id" class="knowledge-hit panel"><span class="hit-number">{{ String(index + 1).padStart(2, '0') }}</span><div><div class="hit-heading"><h3>{{ item.title }}</h3><span class="model-chip">{{ item.retrievalChannels?.join(' + ') || '本地文本检索' }}</span></div><p class="knowledge-excerpt" :class="{ expanded: expanded[item.id] }">{{ item.content }}</p><button v-if="item.content?.length > 220" class="text-link excerpt-toggle" @click="expanded[item.id] = !expanded[item.id]">{{ expanded[item.id] ? '收起片段' : '展开完整片段' }}</button><footer><span>来源：{{ fileName(item.source) }}</span><span>{{ item.id }}</span></footer><small v-if="item.fallbackReason" class="warning-text">部分通道不可用，当前为降级结果。</small></div></article></template>
  </section>
</template>
<script setup>
import { ref, onUnmounted } from "vue";
import { searchKnowledge } from "../services/api";
import { usePlatformStore } from "../stores/platform";
import AppIcon from "../components/common/AppIcon.vue";
const store = usePlatformStore();
const query = ref(''), items = ref([]), loading = ref(false), error = ref(''), searched = ref(false), backend = ref('');
const suggestions = ['序列编码分类器 开放集检测', 'UDP 会话特征', 'VPN 协议识别依据'];
const expanded = ref({});
let version = 0;
const fileName = value => String(value || '').split(/[\\/]/).pop();
async function search() {
  if (store.demoMode || !query.value.trim()) return;
  const id = ++version; loading.value = true; error.value = ''; searched.value = false; items.value = [];
  try { const result = await searchKnowledge(query.value.trim(), 6); if (id === version) { items.value = result.items || []; backend.value = result.knowledgeBackend; searched.value = true; } }
  catch (e) { if (id === version) error.value = e.message || '检索暂时不可用，请重试。'; }
  finally { if (id === version) loading.value = false; }
}
onUnmounted(() => ++version);
</script>
