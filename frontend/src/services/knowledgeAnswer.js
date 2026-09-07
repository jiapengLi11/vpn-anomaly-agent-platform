import { searchPublicKnowledge } from './knowledge';

export const localModelAvailable = ['127.0.0.1', 'localhost'].includes(location.hostname);

export async function askKnowledge(question, history, provider, signal) {
  if (provider === 'deepseek') {
    if (!localModelAvailable) throw new Error('DeepSeek 问答需要在本机运行前端与后端。');
    const response = await fetch('http://127.0.0.1:8090/api/knowledge/answer', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({question, history, provider}), signal,
    });
    if (!response.ok) throw new Error(`问答服务请求失败（${response.status}）。`);
    return response.json();
  }
  const previous = history.filter(h => h.role === 'user');
  const query = question.length < 16 && previous.length ? previous.at(-1).content + ' ' + question : question;
  const { items } = await searchPublicKnowledge(query, 4);
  return { status:items.length ? 'EXTRACTIVE' : 'NO_SOURCES', provider:'demo', sources:items,
    paragraphs:items.slice(0,2).map(item => ({text:item.content, sourceIds:[item.id]})), followUps:[],
    message:items.length ? '当前为资料摘录，尚未调用大模型。启用本地 DeepSeek 后可生成解释性回答。' : '知识库未找到相关资料，请补充具体术语或换个问法。' };
}
