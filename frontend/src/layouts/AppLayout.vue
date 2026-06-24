<script setup lang="ts">
import { Collection, DataAnalysis, Monitor, Search } from "@element-plus/icons-vue";
import { useRoute } from "vue-router";

const route = useRoute();

const navigationItems = [
  { index: "/", label: "知识总览", icon: DataAnalysis },
  { index: "/knowledge", label: "知识库", icon: Collection },
  { index: "/search", label: "全文检索", icon: Search },
  { index: "/system/status", label: "系统状态", icon: Monitor },
];
</script>

<template>
  <ElContainer class="app-shell">
    <ElAside class="app-sidebar" width="248px">
      <RouterLink class="brand" to="/" aria-label="TechBrain 首页">
        <span class="brand__logo">TB</span>
        <span>
          <strong>TechBrain</strong>
          <small>AI 技术知识大脑</small>
        </span>
      </RouterLink>

      <ElMenu
        class="app-menu"
        router
        :default-active="route.path"
        background-color="transparent"
        text-color="#9aa6bf"
        active-text-color="#ffffff"
      >
        <ElMenuItem v-for="item in navigationItems" :key="item.index" :index="item.index">
          <ElIcon>
            <component :is="item.icon" />
          </ElIcon>
          <span>{{ item.label }}</span>
        </ElMenuItem>
      </ElMenu>
    </ElAside>

    <ElContainer>
      <ElHeader class="app-header">
        <div>
          <p class="eyebrow">Personal Knowledge OS</p>
          <h1>{{ route.meta.title ?? "TechBrain" }}</h1>
        </div>
        <ElTag effect="dark" type="success">V0.1 基础版</ElTag>
      </ElHeader>

      <ElMain class="app-main">
        <RouterView />
      </ElMain>
    </ElContainer>
  </ElContainer>
</template>
