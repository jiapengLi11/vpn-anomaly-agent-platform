export async function loadKnowledgeEvaluation(signal) {
  const response = await fetch(`${import.meta.env.BASE_URL}demo/knowledge-evaluation.json`, { signal });
  if (!response.ok) throw new Error('Evaluation unavailable');
  const report = await response.json();
  if (report.scope !== 'SELF_AUTHORED_DEVELOPMENT_SET' || typeof report.metrics?.hitAt3 !== 'number') {
    throw new Error('Invalid evaluation report');
  }
  return report;
}

export async function loadAnswerEvaluation(signal) {
  const response = await fetch(`${import.meta.env.BASE_URL}demo/answer-evaluation.json`, { signal });
  if (!response.ok) throw new Error('Answer evaluation unavailable');
  const report = await response.json();
  if (report.scope !== 'SELF_AUTHORED_DEVELOPMENT_SET' || report.answerMode !== 'EXTRACTIVE' ||
      typeof report.metrics?.abstentionAccuracy !== 'number') {
    throw new Error('Invalid answer evaluation report');
  }
  return report;
}
