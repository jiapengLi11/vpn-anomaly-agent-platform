const STORAGE_KEY = 'vpnBillingSandboxV1';
export const PRICE_VERSION = 'sandbox-2026-09-v1';
export const PRICING = {
  ANALYSIS: { label: '流量分析', baseFen: 50, inputFenPerMillion: 200, outputFenPerMillion: 800 },
  KNOWLEDGE_QA: { label: '知识问答', baseFen: 2, inputFenPerMillion: 100, outputFenPerMillion: 400 },
};
const MAX_BUDGET = { ANALYSIS: [8000, 2200], KNOWLEDGE_QA: [6000, 2200] };

function initialState(now) {
  return { version: 1, balanceFen: 0, freeRemaining: { ANALYSIS: 5, KNOWLEDGE_QA: 5 },
    authorizations: {}, completed: {}, usage: [], orders: [], createdAt: now().toISOString() };
}
function tokenCharge(operation,prompt,completion) { const p=PRICING[operation]; return p.baseFen+
  Math.ceil(prompt*p.inputFenPerMillion/1e6)+Math.ceil(completion*p.outputFenPerMillion/1e6); }

export function createBillingLedger(storage, now=()=>new Date()) {
  function load() { try { const value=JSON.parse(storage?.getItem(STORAGE_KEY)); return value?.version===1 ? value : initialState(now); } catch { return initialState(now); } }
  function save(state) { storage?.setItem(STORAGE_KEY,JSON.stringify(state)); return state; }
  function authorize(operation,requestId) {
    const state=load(); if(state.completed[requestId]) return null; if(state.authorizations[requestId]) return state.authorizations[requestId];
    let mode='FREE_QUOTA',reservedFen=0;
    if(state.freeRemaining[operation]>0) state.freeRemaining[operation]--;
    else { const [input,output]=MAX_BUDGET[operation]; reservedFen=tokenCharge(operation,input,output); mode='PAID_BALANCE';
      if(state.balanceFen<reservedFen) { const error=new Error('免费额度已用完，请前往“用量与计费”充值。'); error.code='INSUFFICIENT_CREDIT'; throw error; }
      state.balanceFen-=reservedFen; }
    const authorization={authorizationId:crypto.randomUUID(),requestId,operation,mode,reservedFen}; state.authorizations[requestId]=authorization; save(state); return authorization;
  }
  function settle(authorization,promptTokens=0,completionTokens=0) {
    if(!authorization) return null; const state=load(); if(state.completed[authorization.requestId]) return state.completed[authorization.requestId];
    const current=state.authorizations[authorization.requestId]; if(!current) throw new Error('计费预授权已失效。'); delete state.authorizations[authorization.requestId];
    const chargeFen=current.mode==='FREE_QUOTA'?0:tokenCharge(current.operation,promptTokens,completionTokens);
    if(current.mode==='PAID_BALANCE') state.balanceFen+=current.reservedFen-chargeFen;
    const usage={usageId:crypto.randomUUID(),requestId:current.requestId,operation:current.operation,billingMode:current.mode,
      promptTokens,completionTokens,totalTokens:promptTokens+completionTokens,chargeFen,occurredAt:now().toISOString(),priceVersion:PRICE_VERSION};
    state.usage.unshift(usage); state.usage=state.usage.slice(0,100); state.completed[current.requestId]=usage; save(state); return usage;
  }
  function release(authorization) { if(!authorization)return; const state=load(),current=state.authorizations[authorization.requestId]; if(!current)return;
    delete state.authorizations[authorization.requestId]; if(current.mode==='FREE_QUOTA')state.freeRemaining[current.operation]++; else state.balanceFen+=current.reservedFen; save(state); }
  function createOrder(channel,amountFen) { if(!['WECHAT','ALIPAY'].includes(channel)||![1000,3000,10000].includes(amountFen))throw new Error('不支持的沙箱订单。');
    const state=load(),created=now(),order={orderId:`PAY-${crypto.randomUUID().slice(0,12).toUpperCase()}`,channel,amountFen,status:'PENDING',environment:'SANDBOX',createdAt:created.toISOString(),expiresAt:new Date(created.getTime()+900000).toISOString()}; state.orders.unshift(order); save(state); return order; }
  function simulatePaid(orderId) { const state=load(),order=state.orders.find(item=>item.orderId===orderId); if(!order)throw new Error('沙箱订单不存在。'); if(order.status!=='PAID'){order.status='PAID';order.paidAt=now().toISOString();state.balanceFen+=order.amountFen;save(state);} return order; }
  function reset() { save(initialState(now)); }
  function summary() { const state=load(),today=new Date(now()); today.setUTCHours(0,0,0,0); const daily=[];
    for(let offset=6;offset>=0;offset--){const date=new Date(today);date.setUTCDate(date.getUTCDate()-offset);const key=date.toISOString().slice(0,10),rows=state.usage.filter(item=>item.occurredAt.slice(0,10)===key);daily.push({date:key,calls:rows.length,tokens:rows.reduce((n,item)=>n+item.totalTokens,0),chargeFen:rows.reduce((n,item)=>n+item.chargeFen,0)});}
    return {...state,dailyUsage:daily,totals:{calls:state.usage.length,tokens:state.usage.reduce((n,item)=>n+item.totalTokens,0),chargeFen:state.usage.reduce((n,item)=>n+item.chargeFen,0)},priceVersion:PRICE_VERSION,pricing:PRICING,paymentEnvironment:'SANDBOX'}; }
  return {authorize,settle,release,createOrder,simulatePaid,reset,summary};
}

export const billingLedger=createBillingLedger(typeof localStorage==='undefined'?null:localStorage);
