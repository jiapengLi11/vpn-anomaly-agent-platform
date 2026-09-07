export function tokenize(text) {
  return (text.toLowerCase().match(/[a-z0-9_]+|[\u4e00-\u9fff]+/g) || []).flatMap(term =>
    /^[\u4e00-\u9fff]+$/.test(term) && term.length > 1
      ? Array.from({ length: term.length - 1 }, (_, i) => term.slice(i, i + 2)) : [term]);
}

export function searchDocuments(documents, query, limit = 6) {
  const terms = new Set(tokenize(query));
  const average = documents.reduce((n, d) => n + d.tokens.length, 0) / (documents.length || 1);
  const frequencies = new Map();
  for (const doc of documents) for (const term of new Set(doc.tokens)) {
    frequencies.set(term, (frequencies.get(term) || 0) + 1);
  }
  const hits = documents.map(({ tokens, ...doc }) => {
    const counts = new Map();
    for (const term of tokens) counts.set(term, (counts.get(term) || 0) + 1);
    let score = 0;
    for (const term of terms) {
      const tf = counts.get(term) || 0;
      if (!tf) continue;
      const df = frequencies.get(term);
      const idf = Math.log(1 + (documents.length - df + 0.5) / (df + 0.5));
      score += idf * tf * 2.5 / (tf + 1.5 * (0.25 + 0.75 * tokens.length / average));
    }
    return { ...doc, score: Math.round(score * 1e6) / 1e6, retrievalChannels: ['BM25'] };
  }).filter(hit => hit.score > 0).sort((a, b) => b.score - a.score || a.id.localeCompare(b.id));
  return { items: hits.slice(0, Math.min(20, Math.max(1, limit))),
    knowledgeBackend: 'browser-bm25', totalChunks: documents.length };
}

let corpus;
export async function searchPublicKnowledge(query, limit) {
  if (!corpus) {
    const response = await fetch(`${import.meta.env.BASE_URL}demo/knowledge.json`);
    if (!response.ok) throw new Error('知识文档加载失败，请重试。');
    corpus = (await response.json()).documents;
  }
  return searchDocuments(corpus, query, limit);
}
