export const MEMORY_KEY = 'vpn-knowledge-conversations-v1';
const TTL = 7 * 24 * 60 * 60 * 1000;

export function cleanSessions(sessions, now = Date.now()) {
  if (!Array.isArray(sessions)) return [];
  return sessions.filter(s => typeof s.id === 'string' && Number.isFinite(s.updatedAt) &&
    s.updatedAt <= now && now - s.updatedAt < TTL && Array.isArray(s.turns))
    .slice(0, 5).map(s => ({ id: s.id, updatedAt: s.updatedAt, turns: s.turns
      .filter(t => t && typeof t.question === 'string' && t.question.length <= 500 &&
        ['SUCCESS', 'EXTRACTIVE'].includes(t.answer?.status) && Array.isArray(t.answer.paragraphs) &&
        t.answer.paragraphs.every(p => p && typeof p.text === 'string' && Array.isArray(p.sourceIds) && p.sourceIds.every(id => typeof id === 'string')) &&
        Array.isArray(t.answer.sources) && t.answer.sources.every(s => s && typeof s.id === 'string' && typeof s.content === 'string') &&
        (!t.answer.followUps || (Array.isArray(t.answer.followUps) && t.answer.followUps.every(q => typeof q === 'string'))))
      .slice(-20).map(t => ({ id: t.id, question: t.question, answer: t.answer, error: '' })) }));
}

export function loadMemory(storage, now = Date.now()) {
  try {
    const raw = storage.getItem(MEMORY_KEY);
    if (!raw) return { enabled: false, sessions: [] };
    if (raw.length > 2000000) throw new Error('Memory too large');
    const sessions = cleanSessions(JSON.parse(raw).sessions, now);
    storage.setItem(MEMORY_KEY, JSON.stringify({ sessions }));
    return { enabled: true, sessions };
  } catch { return { enabled: false, sessions: [], error: '本地记录不可用或已损坏。' }; }
}

export function saveMemory(storage, sessions) {
  try {
    const raw=JSON.stringify({ sessions: cleanSessions(sessions) });
    if(raw.length>2000000) throw new Error('Memory limit');
    storage.setItem(MEMORY_KEY, raw); return '';
  }
  catch { return '浏览器无法保存会话，当前问答仍可继续。'; }
}

export function buildHistory(turns, budget = 8000) {
  const messages = turns.filter(t => ['SUCCESS', 'EXTRACTIVE'].includes(t.answer?.status))
    .flatMap(t => [{ role: 'user', content: t.question },
      { role: 'assistant', content: t.answer.paragraphs.map(p => p.text).join('\n').slice(0, 4000) }])
    .filter(m => m.content).slice(-8);
  const kept = [];
  for (const m of messages.reverse()) {
    if (m.content.length > budget) break;
    kept.unshift(m); budget -= m.content.length;
  }
  return kept;
}
