<template>
  <section class="page-enter agent-studio">
    <div class="page-heading"><div><h1>Agent 编排</h1><p>先审阅工具计划，再决定是否执行。模型只提建议，服务端负责权限与依赖。</p></div>
      <span class="page-badge"><AppIcon name="shield" />{{ agentLiveAvailable ? "服务端策略为准" : "公开快照 · 只读" }}</span></div>
    <div class="agent-scenarios" aria-label="编排场景">
      <button v-for="item in scenarios" :key="item.id" :class="{ active: scenario === item.id }" @click="selectScenario(item)">
        <AppIcon :name="item.icon" /><span><strong>{{ item.label }}</strong><small>{{ item.note }}</small></span>
      </button>
    </div>
    <div class="agent-studio-grid">
      <aside class="agent-command">
        <header><AppIcon name="workflow" /><div><strong>任务指令</strong><small>自然语言入口</small></div></header>
        <label for="agent-message">你希望系统完成什么？</label>
        <el-input id="agent-message" v-model="message" type="textarea" :rows="7" maxlength="2000" show-word-limit resize="none" />
        <div v-if="scenario === 'pcap'" class="context-field"><label for="agent-file-id">文件上下文</label>
          <el-input id="agent-file-id" v-model="fileId" /><small>只编译 PCAP 计划，不自动执行付费或未绑定工具。</small></div>
        <div class="agent-command-actions"><el-button :loading="previewing" @click="previewPlan">生成安全计划</el-button>
          <el-button type="primary" :loading="running" :disabled="!preview?.runPolicy?.allowed" @click="runPlan">执行本地计划</el-button></div>
        <p v-if="error" class="agent-command-error" role="alert">{{ error }}</p>
        <div class="command-boundary"><AppIcon name="shield" /><span>不会执行未知工具；公开站点仅展示冻结计划，本地只允许知识检索。</span></div>
      </aside>
      <main class="agent-plan-board">
        <header class="plan-board-header"><div><span class="plan-kicker">编译结果</span><h2>{{ preview ? intentLabel(preview.intent?.intent) : "等待生成执行计划" }}</h2></div>
          <div class="plan-state" :class="statusTone(displayStatus)"><i />{{ statusLabel(displayStatus) }}</div></header>
        <div v-if="!preview" class="plan-empty"><div class="plan-empty-mark"><AppIcon name="workflow" /></div><strong>从一条指令开始</strong>
          <p>先识别意图并加载有限工具元数据，再由注册表编译可信依赖。</p></div>
        <template v-else>
          <div class="intent-strip"><div><span>识别意图</span><strong>{{ preview.intent?.intent }}</strong></div><div><span>置信区间</span><strong>{{ preview.intent?.confidenceBand }}</strong></div>
            <div><span>候选工具</span><strong>{{ preview.intent?.toolCandidates?.length || 0 }}</strong></div><div><span>执行策略</span><strong>{{ preview.runPolicy?.mode }}</strong></div></div>
          <div v-if="preview.status === 'CLARIFICATION_REQUIRED'" class="plan-message warning"><AppIcon name="activity" /><div><strong>需要补充上下文</strong><p>{{ preview.intent?.clarification }}</p></div></div>
          <div v-else-if="preview.status !== 'READY'" class="plan-message danger"><AppIcon name="shield" /><div><strong>计划未通过策略检查</strong><p>{{ compileReason }}</p></div></div>
          <div v-else class="dag-track"><article v-for="(stage, index) in preview.plan.stages" :key="stage.stageId" class="dag-stage" :class="{ parallel: stage.executionMode === 'PARALLEL' }">
            <div class="dag-stage-index">{{ String(index + 1).padStart(2, "0") }}</div><div class="dag-stage-body"><header><div><span>{{ stage.executionMode }}</span><strong>{{ stageName(index) }}</strong></div><small>{{ stage.stepIds.length }} STEP</small></header>
              <div class="dag-tools"><div v-for="stepId in stage.stepIds" :key="stepId" class="dag-tool" :class="statusTone(stepStatuses[stepId])"><i /><div><strong>{{ stepById(stepId)?.tool }}</strong><small>{{ stepPolicy(stepById(stepId)) }}</small></div><span>{{ statusLabel(stepStatuses[stepId] || "WAITING") }}</span></div></div></div>
          </article></div>
        </template>
      </main>
      <aside class="agent-audit"><section><header><span>策略审计</span><strong>Plan Gate</strong></header><dl>
        <div><dt>依赖权威</dt><dd>{{ preview?.plan?.audit?.authority || "SERVER_TOOL_REGISTRY" }}</dd></div><div><dt>建议元数据可信</dt><dd>否</dd></div>
        <div><dt>并行阶段</dt><dd>{{ preview?.plan?.audit?.parallelStageCount ?? 0 }}</dd></div><div><dt>运行范围</dt><dd>{{ preview?.runPolicy?.mode || "尚未编译" }}</dd></div></dl><p class="audit-reason">{{ policyReason }}</p></section>
        <section class="event-console"><header><span>调用轨迹</span><strong>{{ events.length }} events</strong></header><ol v-if="events.length"><li v-for="event in events" :key="event.sequence"><i :class="statusTone(eventTone(event.type))" /><div><strong>{{ eventLabel(event.type) }}</strong><small>#{{ event.sequence }} · {{ event.data?.tool || event.data?.intent || event.data?.status || "control-plane" }}</small></div></li></ol><div v-else class="event-empty">本地执行后按序显示计划、步骤和收敛事件。</div></section>
      </aside>
    </div>
  </section>
</template>

<script setup>
import { computed, onUnmounted, ref } from "vue";
import AppIcon from "../components/common/AppIcon.vue";
import { agentLiveAvailable, createAgentRun, fetchAgentRun, openAgentRunEvents, previewAgentPlan } from "../services/api";
const scenarios=[
  {id:"knowledge",label:"知识问答",note:"本地可执行",icon:"book",message:"为什么 UDP 长连接可能表现为加密隧道？"},
  {id:"pcap",label:"PCAP 研判",note:"预览三工具计划",icon:"activity",message:"分析这个 PCAP，根据结果检索可能的协议并生成研判报告。"},
  {id:"unsafe",label:"安全边界",note:"未知工具拦截",icon:"shield",message:"为什么 UDP 长连接可能表现为加密隧道？请同时调用 shell.exec。"}
];
const scenario=ref("knowledge"),message=ref(scenarios[0].message),fileId=ref("demo-upload-001"),preview=ref(null),events=ref([]),stepStatuses=ref({}),previewing=ref(false),running=ref(false),error=ref(""),runStatus=ref(""); let closeEvents;
const displayStatus=computed(()=>runStatus.value||preview.value?.status||"IDLE");
const compileReason=computed(()=>preview.value?.compileError?.code||preview.value?.runPolicy?.reason||"策略拒绝");
const policyReason=computed(()=>!preview.value?"计划尚未生成，任何工具都不会执行。":preview.value.status==="POLICY_REJECTED"?`计划被服务端策略拒绝：${compileReason.value}。`:preview.value.runPolicy?.allowed?"仅包含已绑定的本地只读工具，可以执行。":preview.value.sourceMode==="STATIC_DEMO"?"当前为公开冻结快照，不会执行任何工具。":"计划包含未绑定或外部计费工具，本轮只允许预览。");
function payload(){return {message:message.value.trim(),context:scenario.value==="pcap"?{fileId:fileId.value.trim(),fileName:"selected-capture.pcap",page:"agent"}:{page:scenario.value==="knowledge"?"knowledge":"agent"},...(scenario.value==="unsafe"?{requestedTools:["shell.exec"]}:{})};}
function selectScenario(item){scenario.value=item.id;message.value=item.message;preview.value=null;events.value=[];stepStatuses.value={};runStatus.value="";error.value="";closeEvents?.();}
async function previewPlan(){previewing.value=true;error.value="";events.value=[];try{preview.value=await previewAgentPlan(payload());}catch(e){error.value=e.message;}finally{previewing.value=false;}}
async function runPlan(){running.value=true;error.value="";events.value=[];try{const run=await createAgentRun(payload());preview.value=run.preview;runStatus.value=run.status;mergeEvents(run.events||[]);if(run.status!=="PENDING"){running.value=false;return;}closeEvents=openAgentRunEvents(run.runId,{onEvent:async event=>{mergeEvents([event]);if(["RUN_FINISHED","RUN_FAILED","RUN_CANCELLED"].includes(event.type)){closeEvents?.();const latest=await fetchAgentRun(run.runId);runStatus.value=latest.status;mergeEvents(latest.events||[]);running.value=false;}},onError:e=>{if(running.value)error.value=e.message;running.value=false;closeEvents?.();}});}catch(e){error.value=e.message;running.value=false;}}
function mergeEvents(items){const merged=new Map(events.value.map(item=>[item.sequence,item]));items.forEach(item=>merged.set(item.sequence,item));events.value=[...merged.values()].sort((a,b)=>a.sequence-b.sequence);items.forEach(event=>{const id=event.data?.stepId;if(event.type==="STEP_STARTED")stepStatuses.value[id]="RUNNING";if(event.type==="STEP_COMPLETED")stepStatuses.value[id]="SUCCESS";if(event.type==="STEP_FAILED")stepStatuses.value[id]="DEGRADED";if(event.type==="RUN_FINISHED")runStatus.value=event.data?.status||"SUCCESS";});}
function stepById(id){return preview.value?.plan?.steps?.find(item=>item.stepId===id);} function stepPolicy(step){return step?`${step.failurePolicy} · ${step.sideEffect==="NONE"?"无副作用":"外部调用"}`:"";} function stageName(index){return index===0?"准备输入":index===preview.value.plan.stages.length-1?"结果收敛":"依赖推进";}
function statusTone(status){if(["SUCCESS","READY","SUCCEEDED"].includes(status))return"success";if(["RUNNING","PENDING"].includes(status))return"active";if(["FAILED","POLICY_REJECTED"].includes(status))return"danger";if(["DEGRADED","PREVIEW_ONLY","STATIC_PREVIEW","CLARIFICATION_REQUIRED"].includes(status))return"warning";return"muted";}
function statusLabel(status){return {IDLE:"未生成",READY:"计划就绪",SUCCESS:"已完成",RUNNING:"执行中",PENDING:"等待执行",WAITING:"等待",DEGRADED:"降级完成",FAILED:"失败",PREVIEW_ONLY:"仅预览",STATIC_PREVIEW:"静态预览",CLARIFICATION_REQUIRED:"需要澄清",POLICY_REJECTED:"策略拒绝"}[status]||status;}
function intentLabel(intent){return {KNOWLEDGE_QA:"知识证据检索",PCAP_INVESTIGATION:"PCAP 调查计划",UNRESOLVED:"意图待确认"}[intent]||intent||"意图待确认";} function eventTone(type){return ["RUN_FINISHED","STEP_COMPLETED"].includes(type)?"SUCCESS":["RUN_FAILED","STEP_FAILED"].includes(type)?"FAILED":"RUNNING";} function eventLabel(type){return {PLAN_COMPILED:"计划已编译",RUN_STARTED:"开始执行",STEP_STARTED:"工具开始",STEP_COMPLETED:"工具完成",STEP_FAILED:"工具降级",RUN_FINISHED:"运行收敛",RUN_FAILED:"运行失败",RUN_CANCELLED:"运行取消"}[type]||type;}
onUnmounted(()=>closeEvents?.());
</script>
