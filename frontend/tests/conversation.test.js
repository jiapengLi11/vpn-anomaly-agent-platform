import test from 'node:test';
import assert from 'node:assert/strict';
import { consumeSSE } from '../src/services/sse.js';
import { cleanSessions, buildHistory, loadMemory, saveMemory, MEMORY_KEY } from '../src/services/conversationMemory.js';

const turn = { id: '1', question: 'question', answer: { status: 'SUCCESS', paragraphs: [{ text: 'answer', sourceIds: [] }], sources: [] } };
test('memory expires, bounds records and excludes incomplete answers', () => {
  const now = Date.now();
  const sessions = cleanSessions([{ id: 'old', updatedAt: now-8*86400000, turns: [turn] },
    ...Array.from({ length: 7 }, (_, i) => ({ id: String(i), updatedAt: now, turns: [
      ...Array(25).fill(turn), { question: 'cancelled', answer: null }] }))], now);
  assert.equal(sessions.length, 5);
  assert.equal(sessions[0].turns.length, 20);
});
test('memory restores and handles disabled or corrupt storage', () => {
  const data = new Map();
  const storage = { getItem: k => data.get(k), setItem: (k,v) => data.set(k,v) };
  assert.equal(loadMemory(storage).enabled, false);
  assert.equal(saveMemory(storage, [{ id: '1', updatedAt: Date.now(), turns: [turn] }]), '');
  assert.equal(loadMemory(storage).sessions[0].turns[0].question, 'question');
  data.set(MEMORY_KEY, JSON.stringify({sessions:[{id:'1',updatedAt:Date.now(),turns:[{...turn,answer:{...turn.answer,paragraphs:[null]}}]}]}));
  assert.equal(loadMemory(storage).sessions[0].turns.length, 0);
  data.set(MEMORY_KEY, 'bad json');
  assert.equal(loadMemory(storage).enabled, false);
  assert.ok(saveMemory(undefined, []));
});
test('context includes only successful turns with count and character budgets', () => {
  assert.equal(buildHistory([{ question: 'cancelled', answer: null }]).length, 0);
  assert.equal(buildHistory(Array(10).fill(turn)).length, 8);
  assert.ok(buildHistory(Array(10).fill(turn), 15).reduce((n,m) => n+m.content.length,0) <= 15);
});
function response(text, step = 1) {
  const bytes = new TextEncoder().encode(text);
  return new Response(new ReadableStream({ start(controller) {
    for(let i=0;i<bytes.length;i+=step) controller.enqueue(bytes.slice(i,i+step));
    controller.close();
  }}), { headers: { 'content-type': 'text/event-stream' } });
}
test('SSE parses UTF8 across byte boundaries and CRLF', async () => {
  const seen=[];
  const result=await consumeSSE(response('event: draft\r\ndata: {"text":"中文"}\r\n\r\nevent: done\ndata: {"status":"SUCCESS"}\n\n'), (event,data)=>seen.push([event,data]));
  assert.equal(seen[0][1].text, '中文');
  assert.equal(result.status, 'SUCCESS');
});
test('SSE rejects missing final event, server error and non-stream responses', async () => {
  await assert.rejects(consumeSSE(response('event: draft\ndata: {"text":"draft"}\n\n')));
  await assert.rejects(consumeSSE(response('event: error\ndata: {"message":"failed"}\n\n')));
  await assert.rejects(consumeSSE(new Response('{}')));
});
