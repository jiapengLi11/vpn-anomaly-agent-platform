<template>
  <section class="page-enter knowledge-qa">
    <div class="page-heading"><div><h1>知识问答</h1><p>了解流量特征、模型原理与研判方法，回答附带可查看的资料来源。</p></div><el-button :disabled="busy || !turns.length" @click="reset">新对话</el-button></div>
    <div class="qa-layout">
      <div class="panel conversation-panel">
        <div class="qa-mode"><span>{{ provider === 'deepseek' ? 'DeepSeek 知识问答' : '公开资料体验' }}<router-link to="/billing">免费问答 {{ knowledgeRemaining }} / 5</router-link></span><label><input v-model="provider" type="checkbox" true-value="deepseek" false-value="demo" :disabled="!localModelAvailable || busy" />使用本地 DeepSeek</label></div>
        <div class="memory-toolbar">
          <label><input v-model="remember" type="checkbox" :disabled="busy" @change="toggleMemory" />在本机保留会话 7 天</label>
          <select aria-label="历史会话" :value="sessionId" :disabled="busy" @change="switchSession($event.target.value)"><option :value="sessionId" v-if="!sessions.some(s=>s.id===sessionId)">当前新会话</option><option v-for="s in sessions" :key="s.id" :value="s.id">{{ s.turns[0]?.question?.slice(0,28) || '新会话' }}</option></select>
          <button :disabled="busy" @click="clearMemory">清除本机记录</button>
          <small>最多 5 个会话；仅携带当前会话最近 8 条有效消息，上限 8000 字符。不是长期知识记忆。</small>
          <small v-if="memoryError" role="alert">{{ memoryError }}</small>
        </div>
        <div v-if="!turns.length" class="qa-welcome"><h2>你想了解什么？</h2><p>可以问一个概念，也可以继续追问原因、例子和适用边界。</p>
          <div class="topic-list"><button v-for="topic in topics" :key="topic.question" @click="question = topic.question"><span>{{ topic.label }}</span><strong>{{ topic.question }}</strong></button></div>
        </div>
        <div v-else class="qa-turns" aria-live="polite">
          <article v-for="(turn,index) in turns" :key="turn.id" class="qa-turn">
            <div class="user-question"><span>我的问题</span><p>{{ turn.question }}</p></div>
            <div class="assistant-answer"><span class="answer-label">{{ (turn.answer?.provider || turn.provider) === 'deepseek' ? 'DeepSeek 回答' : '知识库参考' }}</span>
              <p v-if="!turn.answer && !turn.error && busy">{{ turn.stage === 'generating' ? '正在生成，草稿尚未完成引用校验…' : '正在检索资料…' }}</p>
              <p v-if="turn.draft" class="stream-draft">{{ turn.draft }}</p>
              <p v-if="turn.error" class="qa-error" role="alert">{{ turn.error }}</p>
              <template v-if="turn.answer">
                <small class="answer-notice">{{ turn.answer.message }}</small>
                <details v-if="turn.answer.queryContext" class="answer-meta"><summary>追问理解与检索词</summary><p>{{ turn.answer.queryContext.strategy === 'FOLLOWUP_ANCHORED' ? '沿用当前会话最近的明确主题' : turn.answer.queryContext.strategy === 'NEEDS_CONTEXT' ? '缺少明确主题，需要补充' : '按本次独立问题检索' }}</p><p>{{ turn.answer.queryContext.query }}</p><small>规则策略，不是模型语义改写；历史回答不作为资料来源。</small></details>
                <div v-for="(paragraph,p) in turn.answer.paragraphs" :key="p" class="answer-paragraph"><p>{{ paragraph.text }}</p><button v-for="id in paragraph.sourceIds" :key="id" class="citation" @click="showSource(index,id)">[{{ sourceNumber(turn,id) }}] 查看来源</button></div>
                <div v-if="turn.answer.followUps?.length" class="follow-ups"><span>继续了解</span><button v-for="q in turn.answer.followUps" :key="q" :disabled="busy" @click="question=q">{{ q }}</button></div>
                <details v-if="turn.answer.model" class="answer-meta"><summary>本次回答信息</summary><p>{{ turn.answer.model }} · {{ turn.answer.elapsedMs }} ms · {{ turn.answer.usage?.total_tokens ?? '未提供' }} tokens</p><p v-if="turn.answer.firstDraftMs != null">首段可见草稿：{{ turn.answer.firstDraftMs }} ms</p><p>引用 ID 已核对；不代表逐句事实校验完成。</p></details>
              </template>
            </div>
          </article>
        </div>
        <form class="qa-composer" @submit.prevent="submit">
          <label for="knowledge-question">{{ turns.length ? '继续提问' : '输入你的问题' }}</label>
          <textarea id="knowledge-question" v-model="question" rows="3" maxlength="500" placeholder="例如：开放集拒识是什么意思？为什么不能把它看作恶意流量？" @keydown.ctrl.enter.prevent="submit" />
          <div><small>{{ localModelAvailable ? '密钥仅由本地后端读取。Ctrl + Enter 发送' : '在线体验展示资料摘录；DeepSeek 需在本机配置密钥后使用。' }}</small><el-button v-if="busy" @click="stop">停止生成</el-button><el-button v-else type="primary" native-type="submit" :disabled="!question.trim()">{{ turns.length ? '发送追问' : '提问' }}</el-button></div>
        </form>
      </div>
      <aside ref="sourcePanel" class="panel qa-sources">
        <h2>回答依据</h2><p class="sources-explainer">点击回答中的引用，查看对应原文。知识资料用于解释，不自动判定当前流量。</p>
        <div v-if="!activeSources.length" class="source-empty">提问后，相关资料会出现在这里。<small>当前收录：特征解释、模型边界、证据引用与人工复核。</small></div>
        <article v-for="(source,index) in activeSources" :key="source.id" :class="{highlighted:source.id===activeId}" class="qa-source"><h3>[{{ index+1 }}] {{ source.title }}</h3><p>{{ source.content }}</p><small>{{ source.source }} / {{ source.section }}</small><details><summary>版本和引用标识</summary><p>{{ source.version }}</p><p>{{ source.id }}</p><p>SHA-256: {{ source.sourceHash }}</p></details></article>
        <section v-if="evaluation" class="quality-baseline">
          <div><span>ENGINEERING BASELINE</span><b>{{ evaluation.passed ? 'PASS' : 'REVIEW' }}</b></div>
          <h2>知识检索开发集</h2>
          <div class="quality-metrics"><p><strong>{{ percent(evaluation.metrics.hitAt1) }}</strong><small>Hit@1</small></p><p><strong>{{ percent(evaluation.metrics.mrr) }}</strong><small>MRR</small></p><p><strong>{{ evaluation.caseCounts.retrieval + evaluation.caseCounts.rejection + evaluation.caseCounts.conversation }}</strong><small>标注场景</small></p></div>
          <small>自编开发集，仅用于防回归，不代表真实业务准确率。</small>
        </section>
        <section v-if="answerEvaluation" class="quality-baseline answer-contract">
          <div><span>ANSWER CONTRACT · EXTRACTIVE</span><b>{{ answerEvaluation.automatedGatePassed ? 'PASS' : 'REVIEW' }}</b></div>
          <h2>回答与拒答合同</h2>
          <div class="quality-metrics"><p><strong>{{ percent(answerEvaluation.metrics.citationValidity) }}</strong><small>引用有效</small></p><p><strong>{{ percent(answerEvaluation.metrics.abstentionAccuracy) }}</strong><small>域外拒答</small></p><p><strong>{{ answerEvaluation.caseCount }}</strong><small>开发案例</small></p></div>
          <small>确定性原文摘录基线，验证评测流水线，不代表 LLM 回答质量。人工复核：{{ answerEvaluation.humanReviewStatus }}。</small>
        </section>
      </aside>
    </div>
  </section>
</template>
<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue';
import { askKnowledge, localModelAvailable } from '../services/knowledgeAnswer';
import { loadMemory, saveMemory, cleanSessions, buildHistory, MEMORY_KEY } from '../services/conversationMemory';
import { loadAnswerEvaluation, loadKnowledgeEvaluation } from '../services/knowledgeEvaluation';
import { billingLedger } from '../services/billingLedger';
const topics = [
  {label:'流量特征', question:'长会话和双向均衡能说明什么？'},
  {label:'模型原理', question:'开放集拒识是什么意思？'},
  {label:'研判方法', question:'为什么调查候选不等于恶意流量？'},
  {label:'知识检索', question:'BM25 为什么有时找不到相关资料？'},
];
let storage;
try { storage=window.localStorage; } catch { /* Privacy mode can disable storage. */ }
const saved=loadMemory(storage);
const remember=ref(saved.enabled), sessions=ref(saved.sessions), memoryError=ref(saved.error || '');
const sessionId=ref(saved.sessions[0]?.id || crypto.randomUUID());
const question=ref(''), turns=ref(saved.sessions[0]?.turns || []), provider=ref('demo'), busy=ref(false), activeTurn=ref(turns.value.length-1), activeId=ref(''), sourcePanel=ref(null);
const evaluation=ref(null), answerEvaluation=ref(null);
const knowledgeRemaining=ref(billingLedger.summary().freeRemaining.KNOWLEDGE_QA);
const activeSources=computed(() => turns.value[activeTurn.value]?.answer?.sources || turns.value[activeTurn.value]?.sources || []);
let controller, stopped=false;
function persist() {
  if(!remember.value) return;
  const entry={id:sessionId.value,updatedAt:Date.now(),turns:turns.value};
  sessions.value=cleanSessions([entry,...sessions.value.filter(s=>s.id!==sessionId.value)]);
  memoryError.value=saveMemory(storage,sessions.value);
}
function toggleMemory() { if(remember.value) persist(); else clearMemory(); }
function clearMemory() {
  try { storage?.removeItem(MEMORY_KEY); memoryError.value=''; }
  catch { memoryError.value='浏览器阻止了清除记录，请通过浏览器设置清除站点数据。'; }
  remember.value=false; sessions.value=[];
}
function switchSession(id) {
  const session=sessions.value.find(s=>s.id===id); if(!session) return;
  sessionId.value=id; turns.value=structuredClone(JSON.parse(JSON.stringify(session.turns)));
  activeTurn.value=turns.value.length-1; activeId.value=''; question.value='';
}
function reset() { persist(); sessionId.value=crypto.randomUUID(); turns.value=[]; activeTurn.value=-1; activeId.value=''; question.value=''; }
function stop() { stopped=true; controller?.abort(); }
function sourceNumber(turn,id) { return (turn.answer.sources || []).findIndex(source=>source.id===id)+1; }
function showSource(index,id) { activeTurn.value=index; activeId.value=id; sourcePanel.value?.scrollIntoView({behavior:'smooth',block:'nearest'}); }
function percent(value) { return `${(value*100).toFixed(value===1 ? 0 : 1)}%`; }
async function submit() {
  if(busy.value || !question.value.trim()) return;
  const text=question.value.trim(); question.value=''; busy.value=true;
  const history=buildHistory(turns.value);
  const turn={id:crypto.randomUUID(),question:text,provider:provider.value,answer:null,error:'',draft:'',stage:'retrieving',sources:[]}; turns.value.push(turn);
  stopped=false; activeTurn.value=turns.value.length-1;
  const current=turns.value.at(-1), requestId=crypto.randomUUID(); let localAuthorization=null; controller=new AbortController();
  const timer=setTimeout(()=>controller.abort(),75000);
  try { if(provider.value==='demo') localAuthorization=billingLedger.authorize('KNOWLEDGE_QA',requestId);
    current.answer=await askKnowledge(text,history,provider.value,controller.signal,(event,data)=>{
    if(event==='draft') current.draft=data.text;
    if(event==='status') current.stage=data.stage;
    if(event==='sources') current.sources=data;
  },requestId); if(localAuthorization && ['SUCCESS','EXTRACTIVE','NO_SOURCES','INSUFFICIENT'].includes(current.answer.status)) billingLedger.settle(localAuthorization); else if(localAuthorization) billingLedger.release(localAuthorization); activeId.value=''; }
  catch(e) { billingLedger.release(localAuthorization); current.error=stopped ? '已停止生成，未完成草稿不会写入记忆。' : e.name==='AbortError' ? '回答超时，请稍后重试。' : e.message || '生成失败或连接中断，未完成草稿已撤回。'; question.value=text; }
  finally { knowledgeRemaining.value=billingLedger.summary().freeRemaining.KNOWLEDGE_QA; current.draft=''; clearTimeout(timer); busy.value=false; persist(); }
}
function refreshQuota(){knowledgeRemaining.value=billingLedger.summary().freeRemaining.KNOWLEDGE_QA}
onMounted(async()=>{ window.addEventListener('billing-updated',refreshQuota); const [retrieval,answers]=await Promise.allSettled([loadKnowledgeEvaluation(),loadAnswerEvaluation()]); evaluation.value=retrieval.status==='fulfilled' ? retrieval.value : null; answerEvaluation.value=answers.status==='fulfilled' ? answers.value : null; });
onUnmounted(()=>{controller?.abort();window.removeEventListener('billing-updated',refreshQuota)});
</script>
<style scoped>
.qa-layout {display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:22px;align-items:start;}
.memory-toolbar {display:flex;flex-wrap:wrap;gap:10px;align-items:center;padding:14px 24px;border-bottom:1px solid #dae5df;font-size:12px;color:#425b67;}.memory-toolbar select {max-width:100%;min-width:0;padding:6px;border:1px solid #cbdcda;background:white;}.memory-toolbar small {flex-basis:100%;}.memory-toolbar button {background:none;border:0;color:#276c74;cursor:pointer;}.stream-draft {white-space:pre-wrap;overflow-wrap:anywhere;border-left:2px solid #5ba836;padding-left:14px;}
.conversation-panel {overflow:hidden;}.qa-mode {display:flex;justify-content:space-between;gap:12px;padding:18px 24px;background:#f0f5f2;border-bottom:1px solid #dae5df;font-size:13px;color:#3c5651;}.qa-mode>span a{margin-left:12px;padding-left:12px;border-left:1px solid #cbdad5;color:#247b80;font-size:10px}.qa-mode label {display:flex;align-items:center;gap:7px;font-size:12px;}
.qa-welcome {padding:38px 30px;}h2 {font-size:21px;margin:0 0 12px;}p {line-height:1.8;color:#425b67;font-size:14px;}small {display:block;line-height:1.7;color:#617782;font-size:12px;}
.topic-list {display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:28px;}.topic-list button {text-align:left;padding:18px;border:1px solid #dce6e4;background:#fafcfb;border-radius:4px;cursor:pointer;}.topic-list span {display:block;font-size:12px;color:#217d86;margin-bottom:8px;}.topic-list strong {font-size:14px;font-weight:500;color:#28444e;line-height:1.6;}.topic-list button:hover {border-color:#5ba836;}
.qa-turns {padding:0 26px;}.qa-turn {padding:24px 0;border-bottom:1px solid #e0e8e8;}.user-question {background:#edf4ef;padding:14px 18px;border-radius:4px;margin-bottom:22px;}.user-question span,.answer-label {font-size:12px;color:#48685e;font-weight:600;}.user-question p {margin:6px 0 0;color:#233f35;white-space:pre-wrap;overflow-wrap:anywhere;}
.answer-paragraph p {white-space:pre-wrap;overflow-wrap:anywhere;}.answer-notice {margin-top:10px;}.citation {border:0;background:#eef6f6;color:#186774;font-size:12px;padding:5px 8px;margin:0 6px 6px 0;border-radius:3px;cursor:pointer;}.follow-ups {display:flex;flex-wrap:wrap;gap:8px;margin-top:20px;font-size:12px;}.follow-ups button {background:white;border:1px solid #ccdedd;padding:7px;color:#276c74;cursor:pointer;}.answer-meta {font-size:12px;margin-top:14px;color:#627881;}.qa-error {color:#a34527;}
.qa-composer {padding:24px;background:#fafcfb;}.qa-composer label {display:block;font-weight:600;font-size:13px;margin-bottom:10px;}.qa-composer textarea {box-sizing:border-box;width:100%;resize:vertical;border:1px solid #cbdcda;border-radius:5px;padding:14px;font:inherit;font-size:14px;line-height:1.7;}.qa-composer textarea:focus {outline:2px solid #2c9298;}.qa-composer>div {display:flex;align-items:center;justify-content:space-between;gap:16px;margin-top:12px;}
.qa-sources {padding:24px;position:sticky;top:90px;}.qa-sources h2 {font-size:17px;}.sources-explainer {font-size:12px;}.source-empty {padding:24px 0;color:#5a717b;font-size:14px;line-height:1.7;}.qa-source {padding:18px 0;border-top:1px solid #dce6e4;}.qa-source h3 {font-size:14px;color:#244b55;line-height:1.6;margin:0;}.qa-source p {font-size:12px;overflow-wrap:anywhere;}.qa-source details {font-size:12px;margin-top:12px;color:#637982;}.qa-source.highlighted {background:#f0f8ef;border-left:3px solid #5ba836;padding-left:12px;}.qa-source small {overflow-wrap:anywhere;}summary {cursor:pointer;}button:focus-visible {outline:2px solid #228997;}
.quality-baseline {margin-top:22px;padding-top:20px;border-top:1px solid #dce6e4;}.quality-baseline>div:first-child {display:flex;justify-content:space-between;color:#65808a;font-size:9px;letter-spacing:.08em;}.quality-baseline>div:first-child b {color:#36875b;}.quality-baseline h2 {margin-top:8px;}.quality-metrics {display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin:14px 0;}.quality-metrics p {margin:0;padding:10px 6px;background:#f3f7f5;text-align:center;}.quality-metrics strong,.quality-metrics small {display:block;}.quality-metrics strong {color:#224e49;font-size:16px;}.quality-metrics small {font-size:9px;}
.answer-contract>div:first-child b {color:#237d86;}.answer-contract .quality-metrics p {background:#eef6f6;}
@media(max-width:1100px) {.qa-layout {grid-template-columns:minmax(0,1fr);}.qa-sources {position:static;}}
@media(max-width:600px) {.qa-mode {flex-direction:column;padding:16px;}.qa-welcome,.qa-composer {padding:20px 16px;}.topic-list {grid-template-columns:1fr;}.qa-turns {padding:0 16px;}.qa-composer>div {align-items:flex-start;}.qa-composer small {max-width:65%;}.qa-sources {padding:20px;}}
</style>
