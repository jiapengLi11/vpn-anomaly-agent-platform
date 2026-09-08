export const STATUS_DISPLAY_MAP = {
  WAITING: "等待中",
  PROCESSING: "处理中",
  SUCCESS: "成功",
  FAILED: "失败",
  CANCELED: "已取消"
};

export const STAGE_DISPLAY_MAP = {
  CREATED: "已创建",
  DISPATCHING: "任务派发",
  PARSING: "流量解析",
  FEATURE_EXTRACTING: "特征提取",
  MODEL_INFERENCING: "模型推理",
  CANDIDATE_FILTERING: "候选筛选",
  REPORT_GENERATING: "报告生成",
  CALLBACK_RECEIVED: "结果回写",
  COMPLETED: "处理完成",
  FAILED: "处理失败"
};

export const TIMELINE_ORDER = [
  { key: "CREATED", label: "已创建", description: "任务记录已创建，等待进入分析链路。" },
  { key: "DISPATCHING", label: "任务派发", description: "Java 主服务将任务派发到 Python 分析服务。" },
  { key: "PARSING", label: "流量解析", description: "解析 PCAP 并抽取会话流。" },
  { key: "FEATURE_EXTRACTING", label: "特征提取", description: "计算统计特征与规则命中。" },
  { key: "MODEL_INFERENCING", label: "模型推理", description: "执行当前模型路线推理。" },
  { key: "CANDIDATE_FILTERING", label: "候选筛选", description: "按证据分组筛选调查候选。" },
  { key: "REPORT_GENERATING", label: "报告生成", description: "生成摘要、报告和结果产物。" },
  { key: "COMPLETED", label: "处理完成", description: "任务已完成，可以查看结果与下载产物。" }
];

export const RULE_DISPLAY_MAP = {
  non_standard_port: "目的端口偏离常见业务端口",
  encrypted_like_without_sni: "流量呈现加密特征但缺少 TLS SNI",
  long_lived_session: "会话持续时间较长",
  balanced_bidirectional_exchange: "上下行收发较为均衡",
  large_packet_burst: "出现异常大的报文突发",
  protocol_distribution: "协议分布概览",
  label_distribution: "标签分布概览"
};

export const KNOWLEDGE_STRATEGY_MAP = {
  baseline_route: "基线文档路线",
  enhancement_route: "增强实验路线",
  default_route: "默认检索路线"
};

export const KNOWLEDGE_TAG_MAP = {
  feature_rules: "基线兼容",
  sequence_encoder: "SEQUENCE_ENCODER",
  pcap: "PCAP",
  report: "报告",
  llm: "LLM",
  mcp: "MCP",
  cash: "cash 路线",
  kunpeng: "kunpeng 路线"
};

export const FUSION_MODE_MAP = {
  FEATURE_ONLY: "仅使用特征证据",
  FEATURE_PLUS_SEQUENCE_ENCODER: "特征证据 + SEQUENCE_ENCODER 结果"
};

export function displayRule(value) {
  return RULE_DISPLAY_MAP[value] || value;
}

export function normalizeRuleText(text) {
  let result = String(text ?? "");
  for (const [key, value] of Object.entries(RULE_DISPLAY_MAP)) {
    result = result.replaceAll(key, value);
  }
  return result;
}

export function formatDateTime(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", { hour12: false });
}

export function formatDuration(seconds) {
  const safe = Number(seconds || 0);
  if (!Number.isFinite(safe) || safe < 0) return "-";
  const hours = Math.floor(safe / 3600);
  const minutes = Math.floor((safe % 3600) / 60);
  const remain = Math.floor(safe % 60);
  if (hours > 0) return `${hours}小时${minutes}分钟${remain}秒`;
  if (minutes > 0) return `${minutes}分钟${remain}秒`;
  return `${remain}秒`;
}

export function formatDistribution(distribution) {
  return Object.entries(distribution || {})
    .map(([key, value]) => `${displayRule(key)}: ${value}`)
    .join(" | ");
}

export function taskAlertType(task) {
  if (task?.status === "SUCCESS") return "success";
  if (task?.status === "FAILED") return "error";
  return "info";
}

export function displayModelType(value) {
  if (value === "SEQUENCE_ENCODER") return "SEQUENCE_ENCODER（主路线）";
  if (value === "FEATURE_RULES") return "FEATURE_RULES（兼容对照）";
  return value || "-";
}

export function displayFusionMode(value) {
  return FUSION_MODE_MAP[value] || value || "未指定";
}

export function displayKnowledgeStrategy(value) {
  return KNOWLEDGE_STRATEGY_MAP[value] || value || "默认检索路线";
}

export function displayKnowledgeTag(value) {
  return KNOWLEDGE_TAG_MAP[value] || value;
}

export function displayKnowledgeSourceFamily(source) {
  const safe = String(source || "");
  if (!safe) return "暂无";
  if (safe.includes("工程开发日志") || safe.includes("设计与优化方案")) return "平台技术说明";
  return "平台知识文档";
}
