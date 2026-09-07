<template>
  <section class="page-enter knowledge-qa">
    <div class="page-heading"><div><h1>知识问答</h1><p>了解流量特征、模型原理与研判方法，回答附带可查看的资料来源。</p></div><el-button :disabled="busy || !turns.length" @click="reset">新对话</el-button></div>
    <div class="qa-layout">
      <div class="panel conversation-panel">
        <div class="qa-mode"><span>{{ provider === 'deepseek' ? 'DeepSeek 知识问答' : '公开资料体验' }}</span><label><input v-model="provider" type="checkbox" true-value="deepseek" false-value="demo" :disabled="!localModelAvailable || busy" />使用本地 DeepSeek</label></div>
        <div v-if="!turns.length" class="qa-welcome"><h2>你想了解什么？</h2><p>可以问一个概念，也可以继续追问原因、例子和适用边界。</p>
          <div class="topic-list"><button v-for="topic in topics" :key="topic.question" @click="question = topic.question"><span>{{ topic.label }}</span><strong>{{ topic.question }}</strong></button></div>
        </div>
        <div v-else class="qa-turns" aria-live="polite">
          <article v-for="(turn,index) in turns" :key="turn.id" class="qa-turn">
            <div class="user-question"><span>我的问题</span><p>{{ turn.question }}</p></div>
            <div class="assistant-answer"><span class="answer-label">{{ turn.answer?.provider === 'deepseek' ? 'DeepSeek 回答' : '知识库参考' }}</span>
              <p v-if="!turn.answer && busy">正在检索资料{{ provider === 'deepseek' ? '并生成回答' : '' }}…</p>
              <p v-if="turn.error" class="qa-error" role="alert">{{ turn.error }}</p>
              <template v-if="turn.answer">
                <small class="answer-notice">{{ turn.answer.message }}</small>
                <div v-for="(paragraph,p) in turn.answer.paragraphs" :key="p" class="answer-paragraph"><p>{{ paragraph.text }}</p><button v-for="id in paragraph.sourceIds" :key="id" class="citation" @click="showSource(index,id)">[{{ sourceNumber(turn,id) }}] 查看来源</button></div>
                <div v-if="turn.answer.followUps?.length" class="follow-ups"><span>继续了解</span><button v-for="q in turn.answer.followUps" :key="q" :disabled="busy" @click="question=q">{{ q }}</button></div>
                <details v-if="turn.answer.model" class="answer-meta"><summary>本次回答信息</summary><p>{{ turn.answer.model }} · {{ turn.answer.elapsedMs }} ms · {{ turn.answer.usage?.total_tokens ?? '未提供' }} tokens</p><p>引用 ID 已核对；不代表逐句事实校验完成。</p></details>
              </template>
            </div>
          </article>
        </div>
        <form class="qa-composer" @submit.prevent="submit">
          <label for="knowledge-question">{{ turns.length ? '继续提问' : '输入你的问题' }}</label>
          <textarea id="knowledge-question" v-model="question" rows="3" maxlength="500" placeholder="例如：开放集拒识是什么意思？为什么不能把它看作恶意流量？" @keydown.ctrl.enter.prevent="submit" />
          <div><small>{{ localModelAvailable ? '密钥仅由本地后端读取。Ctrl + Enter 发送' : '在线体验展示资料摘录；DeepSeek 需在本机配置密钥后使用。' }}</small><el-button type="primary" native-type="submit" :loading="busy" :disabled="!question.trim()">{{ turns.length ? '发送追问' : '提问' }}</el-button></div>
        </form>
      </div>
      <aside ref="sourcePanel" class="panel qa-sources">
        <h2>回答依据</h2><p class="sources-explainer">点击回答中的引用，查看对应原文。知识资料用于解释，不自动判定当前流量。</p>
        <div v-if="!activeSources.length" class="source-empty">提问后，相关资料会出现在这里。<small>当前收录：特征解释、模型边界、证据引用与人工复核。</small></div>
        <article v-for="(source,index) in activeSources" :key="source.id" :class="{highlighted:source.id===activeId}" class="qa-source"><h3>[{{ index+1 }}] {{ source.title }}</h3><p>{{ source.content }}</p><small>{{ source.source }} / {{ source.section }}</small><details><summary>版本和引用标识</summary><p>{{ source.version }}</p><p>{{ source.id }}</p><p>SHA-256: {{ source.sourceHash }}</p></details></article>
      </aside>
    </div>
  </section>
</template>
<script setup>
import { computed, ref, onUnmounted } from 'vue';
import { askKnowledge, localModelAvailable } from '../services/knowledgeAnswer';
const topics = [
  {label:'流量特征', question:'长会话和双向均衡能说明什么？'},
  {label:'模型原理', question:'开放集拒识是什么意思？'},
  {label:'研判方法', question:'为什么调查候选不等于恶意流量？'},
  {label:'知识检索', question:'BM25 为什么有时找不到相关资料？'},
];
const question=ref(''), turns=ref([]), provider=ref('demo'), busy=ref(false), activeTurn=ref(-1), activeId=ref(''), sourcePanel=ref(null);
const activeSources=computed(() => turns.value[activeTurn.value]?.answer?.sources || []);
let controller, serial=0;
function reset() { turns.value=[]; activeTurn.value=-1; activeId.value=''; question.value=''; }
function sourceNumber(turn,id) { return (turn.answer.sources || []).findIndex(source=>source.id===id)+1; }
function showSource(index,id) { activeTurn.value=index; activeId.value=id; sourcePanel.value?.scrollIntoView({behavior:'smooth',block:'nearest'}); }
async function submit() {
  if(busy.value || !question.value.trim()) return;
  const text=question.value.trim(); question.value=''; busy.value=true;
  const history=turns.value.flatMap(t => [{role:'user',content:t.question}, ...(t.answer?.paragraphs?.length ? [{role:'assistant',content:t.answer.paragraphs.map(p=>p.text).join('\n').slice(0,4000)}] : [])]).slice(-8);
  const turn={id:++serial,question:text,answer:null,error:''}; turns.value.push(turn);
  const current=turns.value.at(-1); controller=new AbortController();
  const timer=setTimeout(()=>controller.abort(),75000);
  try { current.answer=await askKnowledge(text,history,provider.value,controller.signal); activeTurn.value=turns.value.length-1; activeId.value=''; }
  catch(e) { current.error=e.name==='AbortError' ? '回答超时，请稍后重试。' : '无法完成问答。请确认本地问答服务运行在 8090 端口，或切换公开资料体验。'; question.value=text; }
  finally { clearTimeout(timer); busy.value=false; }
}
onUnmounted(()=>controller?.abort());
</script>
<style scoped>
.qa-layout {display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:22px;align-items:start;}
.conversation-panel {overflow:hidden;}.qa-mode {display:flex;justify-content:space-between;gap:12px;padding:18px 24px;background:#f0f5f2;border-bottom:1px solid #dae5df;font-size:13px;color:#3c5651;}.qa-mode label {display:flex;align-items:center;gap:7px;font-size:12px;}
.qa-welcome {padding:38px 30px;}h2 {font-size:21px;margin:0 0 12px;}p {line-height:1.8;color:#425b67;font-size:14px;}small {display:block;line-height:1.7;color:#617782;font-size:12px;}
.topic-list {display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:28px;}.topic-list button {text-align:left;padding:18px;border:1px solid #dce6e4;background:#fafcfb;border-radius:4px;cursor:pointer;}.topic-list span {display:block;font-size:12px;color:#217d86;margin-bottom:8px;}.topic-list strong {font-size:14px;font-weight:500;color:#28444e;line-height:1.6;}.topic-list button:hover {border-color:#5ba836;}
.qa-turns {padding:0 26px;}.qa-turn {padding:24px 0;border-bottom:1px solid #e0e8e8;}.user-question {background:#edf4ef;padding:14px 18px;border-radius:4px;margin-bottom:22px;}.user-question span,.answer-label {font-size:12px;color:#48685e;font-weight:600;}.user-question p {margin:6px 0 0;color:#233f35;white-space:pre-wrap;overflow-wrap:anywhere;}
.answer-paragraph p {white-space:pre-wrap;overflow-wrap:anywhere;}.answer-notice {margin-top:10px;}.citation {border:0;background:#eef6f6;color:#186774;font-size:12px;padding:5px 8px;margin:0 6px 6px 0;border-radius:3px;cursor:pointer;}.follow-ups {display:flex;flex-wrap:wrap;gap:8px;margin-top:20px;font-size:12px;}.follow-ups button {background:white;border:1px solid #ccdedd;padding:7px;color:#276c74;cursor:pointer;}.answer-meta {font-size:12px;margin-top:14px;color:#627881;}.qa-error {color:#a34527;}
.qa-composer {padding:24px;background:#fafcfb;}.qa-composer label {display:block;font-weight:600;font-size:13px;margin-bottom:10px;}.qa-composer textarea {box-sizing:border-box;width:100%;resize:vertical;border:1px solid #cbdcda;border-radius:5px;padding:14px;font:inherit;font-size:14px;line-height:1.7;}.qa-composer textarea:focus {outline:2px solid #2c9298;}.qa-composer>div {display:flex;align-items:center;justify-content:space-between;gap:16px;margin-top:12px;}
.qa-sources {padding:24px;position:sticky;top:90px;}.qa-sources h2 {font-size:17px;}.sources-explainer {font-size:12px;}.source-empty {padding:24px 0;color:#5a717b;font-size:14px;line-height:1.7;}.qa-source {padding:18px 0;border-top:1px solid #dce6e4;}.qa-source h3 {font-size:14px;color:#244b55;line-height:1.6;margin:0;}.qa-source p {font-size:12px;overflow-wrap:anywhere;}.qa-source details {font-size:12px;margin-top:12px;color:#637982;}.qa-source.highlighted {background:#f0f8ef;border-left:3px solid #5ba836;padding-left:12px;}.qa-source small {overflow-wrap:anywhere;}summary {cursor:pointer;}button:focus-visible {outline:2px solid #228997;}
@media(max-width:1100px) {.qa-layout {grid-template-columns:minmax(0,1fr);}.qa-sources {position:static;}}
@media(max-width:600px) {.qa-mode {flex-direction:column;padding:16px;}.qa-welcome,.qa-composer {padding:20px 16px;}.topic-list {grid-template-columns:1fr;}.qa-turns {padding:0 16px;}.qa-composer>div {align-items:flex-start;}.qa-composer small {max-width:65%;}.qa-sources {padding:20px;}}
</style>
