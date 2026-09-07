import { demoRequest, isDemoMode } from "./demo";

const DEFAULT_API_BASE = "http://127.0.0.1:8080";
const API_KEY = "vpnApiBaseUrl";

function trimBase(baseUrl) {
  return (baseUrl || DEFAULT_API_BASE).trim().replace(/\/+$/, "");
}

export function getApiBase() {
  return trimBase(localStorage.getItem(API_KEY) || DEFAULT_API_BASE);
}

export function setApiBase(baseUrl) {
  const next = trimBase(baseUrl);
  localStorage.setItem(API_KEY, next);
  return next;
}

export function apiUrl(path) {
  return `${getApiBase()}${path}`;
}

async function request(path, options = {}) {
  if (isDemoMode()) {
    if (options.method && options.method !== "GET") throw new Error("离线演示为只读模式，请连接后端后创建任务。");
    return demoRequest(path);
  }
  const response = await fetch(apiUrl(path), { signal: AbortSignal.timeout(20000), ...options });
  const body = await response.json();
  if (!response.ok || body.success === false) {
    throw new Error(body.message || body.detail || "请求失败");
  }
  return body.data ?? body;
}

export async function fetchHealth() {
  if (isDemoMode()) return demoRequest("/actuator/health");
  const response = await fetch(apiUrl("/actuator/health"), { signal: AbortSignal.timeout(5000) });
  if (!response.ok) throw new Error("后端健康检查失败");
  return response.json();
}

export function fetchWorkbench() { return request("/api/workbench"); }
export function fetchCandidatePage(taskId, filters) {
  return request(`/api/tasks/${encodeURIComponent(taskId)}/candidates?${new URLSearchParams(filters)}`);
}
export function fetchTaskPage(filters = {}) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => { if (value !== "" && value != null) params.set(key, value); });
  return request(`/api/tasks/page?${params}`);
}

export async function fetchRecentTasks() {
  return request("/api/tasks");
}

export async function fetchTask(taskId) {
  return request(`/api/tasks/${taskId}`);
}

export async function fetchTaskPreview(taskId) {
  return request(`/api/tasks/${taskId}/preview`);
}

export async function fetchSameSampleComparison(taskId) {
  return request(`/api/tasks/${taskId}/same-sample-compare`);
}

export async function searchKnowledge(query, limit = 5, modelType = null) {
  const encoded = encodeURIComponent(query);
  const route = modelType
    ? `/api/knowledge/search?q=${encoded}&limit=${limit}&modelType=${encodeURIComponent(modelType)}`
    : `/api/knowledge/search?q=${encoded}&limit=${limit}`;
  return request(route);
}

export async function uploadPcap(file) {
  const formData = new FormData();
  formData.append("file", file);
  return request("/api/files/upload", {
    method: "POST",
    signal: AbortSignal.timeout(120000),
    body: formData
  });
}

export async function createTask(payload) {
  return request("/api/tasks", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
}
