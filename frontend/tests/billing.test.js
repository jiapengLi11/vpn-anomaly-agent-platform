import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createBillingLedger } from '../src/services/billingLedger.js';

function memoryStorage() { let value; return { getItem:()=>value, setItem:(_,next)=>{value=next} }; }
const fixedNow=()=>new Date('2026-09-08T08:00:00Z');

test('new browser account receives five free uses per operation',()=>{
  const ledger=createBillingLedger(memoryStorage(),fixedNow);
  for(let i=0;i<5;i++) ledger.settle(ledger.authorize('KNOWLEDGE_QA',`q-${i}`),100,20);
  assert.equal(ledger.summary().freeRemaining.KNOWLEDGE_QA,0);
  assert.equal(ledger.summary().freeRemaining.ANALYSIS,5);
  assert.throws(()=>ledger.authorize('KNOWLEDGE_QA','q-6'),error=>error.code==='INSUFFICIENT_CREDIT');
});

test('sandbox recharge and callback are idempotent',()=>{
  const ledger=createBillingLedger(memoryStorage(),fixedNow);
  const order=ledger.createOrder('ALIPAY',3000);
  ledger.simulatePaid(order.orderId); ledger.simulatePaid(order.orderId);
  assert.equal(ledger.summary().balanceFen,3000);
  assert.equal(ledger.summary().orders[0].environment,'SANDBOX');
});

test('failed authorization is released and daily usage is aggregated',()=>{
  const ledger=createBillingLedger(memoryStorage(),fixedNow);
  const cancelled=ledger.authorize('ANALYSIS','cancelled'); ledger.release(cancelled);
  const completed=ledger.authorize('ANALYSIS','completed'); ledger.settle(completed,1200,300);
  const summary=ledger.summary();
  assert.equal(summary.freeRemaining.ANALYSIS,4);
  assert.equal(summary.totals.calls,1);
  assert.equal(summary.dailyUsage.at(-1).tokens,1500);
  assert.equal(summary.dailyUsage.at(-1).calls,1);
});
