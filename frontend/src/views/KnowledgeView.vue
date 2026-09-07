<template>
  <section class="page-enter">
    <div class="page-heading"><div><h1>知识检索</h1><p>查找特征解释与研判边界，追溯每条参考依据。</p></div><span class="page-badge"><AppIcon name="book" />知识参考，不替代流量事实</span></div>
    <div class="knowledge-search panel">
      <div class="knowledge-mark"><AppIcon name="search" /></div>
      <h2>你想查找哪类研判依据？</h2><p>输入特征、规则代码或完整问题。</p>
      <form @submit.prevent="search">
        <el-input v-model="query" clearable size="large" maxlength="500" placeholder="例如：UDP 会话特征" aria-label="知识检索问题" />
        <el-button type="primary" size="large" :loading="loading" :disabled="!query.trim()" native-type="submit">检索文档<AppIcon name="arrow" /></el-button>
      </form>
      <div class="suggested-queries"><span>试试这些</span><button v-for="q in suggestions" :key="q" @click="query = q; search()">{{ q }}</button></div>
    </div>
    <div v-if="store.demoMode" class="notice notice-info"><AppIcon name="book" /><span>搜索本仓库自编示例文档，查询在浏览器内完成。当前为 BM25 词法检索，尚未接入语义向量。</span></div>
    <div v-if="error" class="notice notice-warning" role="alert">{{ error }}</div>
    <template v-if="searched && !error">
      <div class="result-count" aria-live="polite">检索到 {{ items.length }} 个文档片段<span>后端：{{ backend }}</span></div>
      <el-empty v-if="!items.length" description="暂无匹配内容，请尝试规则代码或更明确的特征。" />
      <article v-for="(item, index) in items" :key="item.id" class="knowledge-hit panel">
        <span class="hit-number">{{ String(index + 1).padStart(2, '0') }}</span>
        <div>
          <div class="hit-heading"><h3>{{ item.title }}</h3><span class="model-chip">{{ item.retrievalChannels?.join(' + ') }}</span></div>
          <p class="knowledge-excerpt" :class="{ expanded: expanded[item.id] }">{{ item.content }}</p>
          <button v-if="item.content?.length > 220" class="text-link excerpt-toggle" @click="expanded[item.id] = !expanded[item.id]">{{ expanded[item.id] ? '收起片段' : '展开完整片段' }}</button>
          <footer><span>来源：{{ fileName(item.source) }} · {{ item.section }}</span><span>{{ item.id }}</span></footer>
          <small>版本 {{ item.version }} · 相关度 {{ item.score?.toFixed(3) }}（非概率）</small>
          <details><summary>查看来源校验信息</summary><p style="overflow-wrap:anywhere">SHA-256：{{ item.sourceHash }}</p><p>自编示例文档，只作解释参考。</p></details>
        </div>
      </article>
    </template>
  </section>
</template>
<script setup>
import { ref, onUnmounted } from 'vue';
import { searchKnowledge } from '../services/api';
import { usePlatformStore } from '../stores/platform';
import AppIcon from '../components/common/AppIcon.vue';
const store = usePlatformStore();
const query = ref(''), items = ref([]), loading = ref(false), error = ref(''), searched = ref(false), backend = ref('');
const suggestions = ['开放集拒识', 'UDP 会话特征', 'LONG_SESSION', '调查候选 恶意结论'];
const expanded = ref({});
let version = 0;
const fileName = value => String(value || '').split(/[\\/]/).pop();
async function search() {
  if (!query.value.trim()) return;
  const id = ++version; loading.value = true; error.value = ''; searched.value = false; items.value = [];
  try {
    const result = await searchKnowledge(query.value.trim(), 6);
    if (id === version) { items.value = result.items || []; backend.value = result.knowledgeBackend; searched.value = true; }
  } catch (e) { if (id === version) error.value = e.message || '检索暂时不可用，请重试。'; }
  finally { if (id === version) loading.value = false; }
}
onUnmounted(() => ++version);
</script>
