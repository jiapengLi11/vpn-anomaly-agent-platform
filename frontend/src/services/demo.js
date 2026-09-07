import { searchPublicKnowledge } from './knowledge';
let snapshot;
export function isDemoMode() {
  const saved = localStorage.getItem("vpnDemoMode");
  return saved == null ? true : saved === "true";
}
export function setDemoMode(value) { localStorage.setItem("vpnDemoMode", String(value)); }
async function load() {
  if (!snapshot) {
    const response = await fetch(`${import.meta.env.BASE_URL}demo/workspace.json`);
    if (!response.ok) throw new Error("离线示例尚未生成，请先运行 build_frontend_demo.py。");
    snapshot = await response.json();
  }
  return snapshot;
}
export async function demoRequest(path) {
  const url = new URL(path, "http://local.invalid");
  if (url.pathname === '/api/knowledge/search') {
    return searchPublicKnowledge(url.searchParams.get('q') || '', Number(url.searchParams.get('limit') || 6));
  }
  const data = await load();
  if (url.pathname === "/actuator/health") return { status: "DEMO" };
  if (url.pathname === "/api/workbench") return { taskCount: data.tasks.length,
    statusCounts: { SUCCESS: data.tasks.length, PROCESSING: 0, WAITING: 0, FAILED: 0, CANCELED: 0 },
    recentTasks: data.tasks.slice(0, 6), scope: "SYNTHETIC_READ_ONLY" };
  if (url.pathname === "/api/tasks") return data.tasks;
  const candidate = url.pathname.match(/^\/api\/tasks\/([^/]+)\/candidates$/);
  if (candidate) {
    const records = data.previews[candidate[1]]?.offlineDecisions;
    if (!records) throw new Error("当前任务没有完整候选决策文件。");
    const page = Number(url.searchParams.get("page") || 1), pageSize = Number(url.searchParams.get("pageSize") || 10);
    const decision = url.searchParams.get("decision") ?? "CANDIDATE";
    const keyword = (url.searchParams.get("keyword") || "").trim().toLowerCase();
    const decisionCounts = { CANDIDATE: 0, OBSERVE: 0, PASS: 0 };
    records.forEach(row => decisionCounts[row.decision]++);
    const matches = records.filter(row => (!decision || row.decision === decision) && row.flowId.toLowerCase().includes(keyword));
    return { items: matches.slice((page - 1) * pageSize, page * pageSize), total: matches.length,
      page, pageSize, totalPages: Math.ceil(matches.length / pageSize), totalRecords: records.length, decisionCounts };
  }
  if (url.pathname === "/api/tasks/page") {
    const page = Number(url.searchParams.get("page") || 1), pageSize = Number(url.searchParams.get("pageSize") || 10);
    const keyword = (url.searchParams.get("keyword") || "").toLowerCase();
    const items = data.tasks.filter(task => (!url.searchParams.get("status") || task.status === url.searchParams.get("status"))
      && (!url.searchParams.get("modelType") || task.modelType === url.searchParams.get("modelType"))
      && `${task.taskId} ${task.fileName}`.toLowerCase().includes(keyword));
    return { items: items.slice((page - 1) * pageSize, page * pageSize), total: items.length, page, pageSize,
      totalPages: Math.ceil(items.length / pageSize) };
  }
  const match = url.pathname.match(/^\/api\/tasks\/([^/]+)(\/preview|\/same-sample-compare)?$/);
  if (match) {
    const task = data.tasks.find(item => item.taskId === match[1]);
    if (!task) throw new Error("当前离线示例没有这条任务。");
    return match[2] === "/preview" ? data.previews[task.taskId] : match[2] ? {} : task;
  }
  throw new Error("离线演示仅提供已保存的任务和报告；此功能需要连接本地服务。");
}
