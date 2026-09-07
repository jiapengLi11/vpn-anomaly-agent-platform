export function dateTime(value) {
  if (!value) return '--';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '--' : date.toLocaleString('zh-CN', { hour12: false, month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
}
export function duration(seconds) {
  if (seconds == null) return '--';
  return seconds < 60 ? `${seconds} 秒` : `${Math.floor(seconds / 60)} 分 ${seconds % 60} 秒`;
}
export function backendName(value) {
  return ({ SEQUENCE_ENCODER_DEMO: '序列编码分类器 兼容演示模型', SEQUENCE_ENCODER_WITH_BASELINE_AUGMENT: '序列编码分类器 + 特征辅助', SEQUENCE_ENCODER: '序列编码分类器', DecisionTreeClassifier: '决策树（兼容对照）', FEATURE_RULES_FALLBACK: '基线回退', FEATURE_RULES_AUGMENT_ONLY: '仅特征辅助' })[value] || value || '尚无执行记录';
}
export const modeName = value => value === 'FEATURE_PLUS_SEQUENCE_ENCODER' ? '特征 + 序列编码分类器' : '仅特征证据';
