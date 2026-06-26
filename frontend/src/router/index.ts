import type { RouteRecordRaw } from "vue-router";
import { createRouter, createWebHistory } from "vue-router";

import AppLayout from "@/layouts/AppLayout.vue";

const routes: RouteRecordRaw[] = [
  {
    path: "/",
    component: AppLayout,
    children: [
      {
        path: "",
        name: "dashboard",
        component: () => import("@/views/DashboardView.vue"),
        meta: { title: "知识总览" },
      },
      {
        path: "knowledge",
        name: "knowledge",
        component: () => import("@/views/KnowledgeView.vue"),
        meta: { title: "知识库" },
      },
      {
        path: "search",
        name: "search",
        component: () => import("@/views/SearchView.vue"),
        meta: { title: "全文检索" },
      },
      {
        path: "system/status",
        name: "system-status",
        component: () => import("@/views/SystemStatusView.vue"),
        meta: { title: "系统状态" },
      },
      {
        path: "system/sync",
        name: "system-sync",
        component: () => import("@/views/KnowledgeSyncView.vue"),
        meta: { title: "同步管理" },
      },
    ],
  },
  {
    path: "/:pathMatch(.*)*",
    name: "not-found",
    component: () => import("@/views/NotFoundView.vue"),
    meta: { title: "页面不存在" },
  },
];

export const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 };
  },
});

router.afterEach((to) => {
  const title = to.meta.title ? `${String(to.meta.title)} - TechBrain` : "TechBrain";
  document.title = title;
});
