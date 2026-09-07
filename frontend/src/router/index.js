import { createRouter, createWebHashHistory } from "vue-router";
export default createRouter({
  history: createWebHashHistory(),
  scrollBehavior: () => ({ top: 0 }),
  routes: [
    { path: "/", redirect: "/overview" },
    { path: "/overview", component: () => import("../views/OverviewView.vue") },
    { path: "/tasks", component: () => import("../views/TaskCenterView.vue") },
    { path: "/tasks/:taskId", component: () => import("../views/ResultCenterView.vue") },
    { path: "/reports", component: () => import("../views/TaskCenterView.vue") },
    { path: "/knowledge", component: () => import("../views/KnowledgeView.vue") },
    { path: "/results", redirect: "/reports" },
    { path: "/:pathMatch(.*)*", redirect: "/overview" }
  ]
});
