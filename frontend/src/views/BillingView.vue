<template>
  <section class="page-enter billing-page">
    <div class="page-heading"><div><h1>用量与计费</h1><p>查看免费额度、模型 token、费用与沙箱支付流水。</p></div><el-button type="primary" @click="openRecharge">账户充值</el-button></div>
    <div class="billing-hero panel">
      <div class="balance-block"><span>可用余额</span><strong><small>¥</small>{{ money(summary.balanceFen) }}</strong><p>沙箱账户 · 不产生真实资金交易</p></div>
      <div class="quota-rail">
        <article v-for="item in quotas" :key="item.key"><div><span>{{ item.label }}</span><strong>{{ item.remaining }} / 5 次</strong></div><div class="rail"><i :style="{width:`${item.remaining*20}%`}" /></div><small>{{ item.remaining ? '优先抵扣免费次数' : '后续按价格版本结算' }}</small></article>
      </div>
      <div class="billing-seal"><AppIcon name="wallet" /><span>计费策略</span><strong>{{ summary.priceVersion }}</strong><small>预授权 → 执行 → 实际结算</small></div>
    </div>

    <div class="billing-grid">
      <section class="panel usage-panel"><div class="billing-section-head"><div><h2>近 7 日 token 使用</h2><p>输入与输出合并展示；免费调用同样记录 token。</p></div><strong>{{ number(summary.totals.tokens) }}</strong></div>
        <div class="usage-chart" aria-label="近 7 日 token 柱状图"><article v-for="day in summary.dailyUsage" :key="day.date"><span>{{ day.tokens ? number(day.tokens) : '' }}</span><div><i :style="{height:barHeight(day.tokens)}" /></div><small>{{ day.date.slice(5) }}</small></article></div>
        <div v-if="!summary.totals.calls" class="billing-empty">完成分析或知识问答后，用量会按天写入这里。</div>
      </section>
      <aside class="panel pricing-panel"><div class="billing-section-head"><div><h2>当前价格</h2><p>人民币计价，token 单价按每百万个。</p></div></div>
        <article v-for="(price,key) in summary.pricing" :key="key"><div><AppIcon :name="key==='ANALYSIS'?'activity':'book'" /><strong>{{ price.label }}</strong></div><p><span>基础费</span><b>¥{{ money(price.baseFen) }} / 次</b></p><p><span>输入 token</span><b>¥{{ money(price.inputFenPerMillion) }} / 1M</b></p><p><span>输出 token</span><b>¥{{ money(price.outputFenPerMillion) }} / 1M</b></p></article>
        <small>价格仅用于沙箱演示，不对应任何模型厂商公开报价。</small>
      </aside>
    </div>

    <section class="panel ledger-panel"><div class="billing-section-head"><div><h2>用量流水</h2><p>成功请求才结算；失败、取消和重复 requestId 不重复扣费。</p></div><button class="text-action" @click="resetSandbox">重置新用户</button></div>
      <div v-if="!summary.usage.length" class="billing-empty">当前没有用量记录。新用户已获得 5 次分析和 5 次知识问答。</div>
      <div v-else class="ledger-table"><div class="ledger-row ledger-head"><span>时间</span><span>类型</span><span>Token</span><span>计费方式</span><span>费用</span></div><div v-for="row in summary.usage" :key="row.usageId" class="ledger-row"><span>{{ time(row.occurredAt) }}</span><span>{{ label(row.operation) }}</span><span>{{ number(row.totalTokens) }}</span><span>{{ row.billingMode==='FREE_QUOTA'?'免费额度':'账户余额' }}</span><strong>¥{{ money(row.chargeFen) }}</strong></div></div>
    </section>

    <el-dialog v-model="checkoutOpen" width="min(560px, 92vw)" title="沙箱账户充值" class="checkout-dialog">
      <div v-if="!order"><p class="checkout-note">选择金额与通道。创建的是演示订单，不会拉起微信或支付宝，也不会产生真实扣款。</p>
        <div class="amount-options"><button v-for="amount in [1000,3000,10000]" :key="amount" :class="{active:amountFen===amount}" @click="amountFen=amount"><strong>¥{{ money(amount) }}</strong><small>{{ amount===3000?'演示推荐':'账户余额' }}</small></button></div>
        <div class="channel-options"><button :class="{active:channel==='WECHAT'}" @click="channel='WECHAT'"><i class="wechat" />微信支付<span>沙箱</span></button><button :class="{active:channel==='ALIPAY'}" @click="channel='ALIPAY'"><i class="alipay" />支付宝<span>沙箱</span></button></div>
      </div>
      <div v-else class="sandbox-cashier"><div class="cashier-mark"><AppIcon name="shield" /></div><span>{{ order.channel==='WECHAT'?'微信支付':'支付宝' }}沙箱订单</span><strong>¥{{ money(order.amountFen) }}</strong><code>{{ order.orderId }}</code><p>真实系统应在服务端验签异步回调后入账；此处点击按钮模拟合法回调。</p></div>
      <template #footer><el-button @click="checkoutOpen=false">取消</el-button><el-button v-if="!order" type="primary" @click="createOrder">创建沙箱订单</el-button><el-button v-else type="primary" @click="pay">模拟支付成功</el-button></template>
    </el-dialog>
  </section>
</template>
<script setup>
import { computed, ref } from 'vue';
import { ElMessageBox } from 'element-plus';
import AppIcon from '../components/common/AppIcon.vue';
import { billingLedger } from '../services/billingLedger';
const summary=ref(billingLedger.summary()),checkoutOpen=ref(false),amountFen=ref(3000),channel=ref('WECHAT'),order=ref(null);
const quotas=computed(()=>[{key:'ANALYSIS',label:'流量分析',remaining:summary.value.freeRemaining.ANALYSIS},{key:'KNOWLEDGE_QA',label:'知识问答',remaining:summary.value.freeRemaining.KNOWLEDGE_QA}]);
function money(fen){return (fen/100).toFixed(2)} function number(value){return new Intl.NumberFormat('zh-CN').format(value)}
function label(key){return summary.value.pricing[key]?.label||key} function time(value){return new Date(value).toLocaleString('zh-CN',{hour12:false})}
function barHeight(value){const max=Math.max(...summary.value.dailyUsage.map(day=>day.tokens),1);return `${Math.max(value/max*100,value?8:2)}%`}
function refresh(){summary.value=billingLedger.summary();window.dispatchEvent(new CustomEvent('billing-updated'))}
function openRecharge(){order.value=null;checkoutOpen.value=true} function createOrder(){order.value=billingLedger.createOrder(channel.value,amountFen.value)}
function pay(){billingLedger.simulatePaid(order.value.orderId);refresh();checkoutOpen.value=false}
async function resetSandbox(){await ElMessageBox.confirm('将清空沙箱余额、订单和用量，并恢复新用户各 5 次免费额度。','重置沙箱账户',{confirmButtonText:'确认重置',cancelButtonText:'取消'});billingLedger.reset();refresh()}
</script>
<style scoped>
.billing-page{max-width:1440px}.billing-hero{display:grid;grid-template-columns:1.05fr 1.55fr .8fr;min-height:235px;background:linear-gradient(112deg,#102c35,#17434a 62%,#176465);color:white;overflow:hidden}.balance-block{padding:38px;border-right:1px solid #ffffff1f}.balance-block>span,.billing-seal span{font-size:11px;color:#9bc0c3}.balance-block>strong{display:block;margin:12px 0 8px;font-size:48px;font-weight:500;letter-spacing:-2px}.balance-block>strong small{font-size:20px;margin-right:8px}.balance-block p,.billing-seal small{font-size:11px;color:#8fb0b5}.quota-rail{display:grid;gap:28px;padding:38px}.quota-rail article>div:first-child{display:flex;justify-content:space-between}.quota-rail span{font-size:13px;color:#cce0df}.quota-rail strong{font-size:13px}.rail{height:5px;margin:12px 0 8px;background:#ffffff1a}.rail i{display:block;height:100%;background:#67c83d}.quota-rail small{font-size:10px;color:#8fb0b5}.billing-seal{display:flex;flex-direction:column;justify-content:center;padding:32px;border-left:1px solid #ffffff1f;background:#ffffff08}.billing-seal svg{width:30px;height:30px;color:#70d7cf;margin-bottom:20px}.billing-seal strong{font-size:13px;margin:7px 0}.billing-grid{display:grid;grid-template-columns:minmax(0,1.7fr) minmax(300px,.8fr);gap:18px;margin-top:18px}.usage-panel,.pricing-panel,.ledger-panel{padding:28px 30px}.billing-section-head{display:flex;justify-content:space-between;gap:20px;align-items:start}.billing-section-head h2{font-size:17px}.billing-section-head p{margin-top:7px;font-size:11px;color:#81949b}.billing-section-head>strong{font-size:28px;color:#1f5457}.usage-chart{display:grid;grid-template-columns:repeat(7,1fr);gap:15px;height:190px;margin-top:26px}.usage-chart article{display:grid;grid-template-rows:20px 1fr 18px;text-align:center}.usage-chart article>span,.usage-chart small{font-size:9px;color:#81949b}.usage-chart article>div{display:flex;align-items:end;justify-content:center;border-bottom:1px solid #dce6e4;background:linear-gradient(#fff,#f5f9f8)}.usage-chart i{width:min(30px,60%);min-height:2px;background:#3aa5a2;border-top:3px solid #64c83c}.pricing-panel article{padding:20px 0;border-top:1px solid #e1e8e6}.pricing-panel article>div{display:flex;align-items:center;gap:9px;margin-bottom:12px;color:#244b50}.pricing-panel article p{display:flex;justify-content:space-between;margin:7px 0;font-size:11px;color:#74888e}.pricing-panel article b{font-weight:500;color:#344f55}.pricing-panel>small{font-size:10px;color:#8a9a9e}.ledger-panel{margin-top:18px}.text-action{border:0;background:none;color:#247f83;font-size:11px}.billing-empty{padding:35px 0;color:#84979d;font-size:12px}.ledger-row{display:grid;grid-template-columns:1.3fr 1fr .8fr 1fr .6fr;gap:14px;padding:14px 0;border-top:1px solid #e3e9e7;font-size:11px;color:#526b72}.ledger-head{margin-top:18px;color:#91a0a4;font-size:9px}.ledger-row strong{text-align:right;color:#274e50}.amount-options,.channel-options{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:18px 0}.amount-options button,.channel-options button{padding:18px;border:1px solid #d9e3e0;background:white;text-align:left}.amount-options button.active,.channel-options button.active{border-color:#46a66d;box-shadow:inset 0 -3px #55aa2f}.amount-options strong,.amount-options small{display:block}.amount-options small{margin-top:6px;color:#829398;font-size:10px}.channel-options{grid-template-columns:1fr 1fr}.channel-options button{display:flex;align-items:center;gap:9px}.channel-options button span{margin-left:auto;font-size:9px;color:#8b999e}.channel-options i{width:9px;height:9px;border-radius:50%}.wechat{background:#16a060}.alipay{background:#1677ff}.checkout-note{font-size:12px;line-height:1.8;color:#5f747a}.sandbox-cashier{text-align:center;padding:25px}.cashier-mark{display:grid;place-items:center;width:58px;height:58px;margin:auto;background:#eaf6f2;color:#258f75}.sandbox-cashier>span,.sandbox-cashier code,.sandbox-cashier p{display:block;margin-top:12px}.sandbox-cashier>strong{display:block;margin:12px;font-size:35px}.sandbox-cashier p{color:#72858b;font-size:11px;line-height:1.8}.sandbox-cashier code{font-size:10px;color:#547078}@media(max-width:1000px){.billing-hero{grid-template-columns:1fr 1.3fr}.billing-seal{grid-column:1/-1;border-left:0;border-top:1px solid #ffffff1f;padding:20px 32px}.billing-seal svg{display:none}.billing-grid{grid-template-columns:1fr}}@media(max-width:600px){.billing-hero{grid-template-columns:1fr}.balance-block{border-right:0;border-bottom:1px solid #ffffff1f;padding:28px 22px}.balance-block>strong{font-size:40px}.quota-rail{padding:25px 22px}.billing-seal{padding:18px 22px}.usage-panel,.pricing-panel,.ledger-panel{padding:22px 18px}.usage-chart{gap:5px}.ledger-table{overflow:auto}.ledger-row{min-width:620px}.amount-options{grid-template-columns:1fr}.channel-options{grid-template-columns:1fr}}
</style>
