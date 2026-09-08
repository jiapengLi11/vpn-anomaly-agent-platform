import { searchPublicKnowledge } from './knowledge';
import { consumeSSE } from './sse';
import { resolveQuery } from './queryContext';

export const localModelAvailable = ['127.0.0.1', 'localhost'].includes(location.hostname);

export async function askKnowledge(question, history, provider, signal, onEvent) {
  if (provider === 'deepseek') {
    if (!localModelAvailable) throw new Error('DeepSeek 问答需要在本机运行前端与后端。');
    const response = await fetch('http://127.0.0.1:8090/api/knowledge/answer/stream', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({question, history, provider}), signal,
    });
    if (!response.ok) throw new Error(`问答服务请求失败（${response.status}）。`);
    return consumeSSE(response, onEvent);
  }
  const context=resolveQuery(question, history), query=context.query;
  if(context.strategy==='NEEDS_CONTEXT') return {status:'NEEDS_CONTEXT',queryContext:context,provider:'demo',sources:[],paragraphs:[],followUps:[],message:'请先说明你想继续了解的主题，例如：开放集拒识有什么局限？'};
  const { items } = await searchPublicKnowledge(query, 4);
  return { status:items.length ? 'EXTRACTIVE' : 'NO_SOURCES', provider:'demo', sources:items, queryContext:context,
    paragraphs:items.slice(0,2).map(item => ({text:item.content, sourceIds:[item.id]})), followUps:[],
    message:items.length ? '当前为资料摘录，尚未调用大模型。启用本地 DeepSeek 后可生成解释性回答。' : '知识库未找到相关资料，请补充具体术语或换个问法。' };
}
