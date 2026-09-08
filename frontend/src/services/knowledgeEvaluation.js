export async function loadKnowledgeEvaluation(signal) {
  const response = await fetch(`${import.meta.env.BASE_URL}demo/knowledge-evaluation.json`, { signal });
  if (!response.ok) throw new Error('Evaluation unavailable');
  const report = await response.json();
  if (report.scope !== 'SELF_AUTHORED_DEVELOPMENT_SET' || typeof report.metrics?.hitAt3 !== 'number') {
    throw new Error('Invalid evaluation report');
  }
  return report;
}
