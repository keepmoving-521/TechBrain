<script setup lang="ts">
import { computed, onMounted } from "vue";

import { useSystemStore } from "@/stores/system";

const systemStore = useSystemStore();

const statusType = computed(() => {
  if (systemStore.loading) {
    return "info";
  }
  return systemStore.health?.status === "ok" ? "success" : "danger";
});

onMounted(() => {
  void systemStore.refreshHealth();
});
</script>

<template>
  <ElCard shadow="never" class="content-card">
    <template #header>
      <div class="card-header">
        <span>后端健康检查</span>
        <ElButton :loading="systemStore.loading" @click="systemStore.refreshHealth">
          重新检查
        </ElButton>
      </div>
    </template>

    <ElAlert
      :title="systemStore.health ? '后端服务可访问' : '尚未获取到后端状态'"
      :type="statusType"
      :closable="false"
      show-icon
    />

    <ElDescriptions v-if="systemStore.health" class="status-descriptions" :column="1" border>
      <ElDescriptionsItem label="服务">{{ systemStore.health.service }}</ElDescriptionsItem>
      <ElDescriptionsItem label="版本">{{ systemStore.health.version }}</ElDescriptionsItem>
      <ElDescriptionsItem label="环境">{{ systemStore.health.environment }}</ElDescriptionsItem>
      <ElDescriptionsItem label="状态">{{ systemStore.health.status }}</ElDescriptionsItem>
    </ElDescriptions>

    <ElText v-if="systemStore.lastError" class="status-error" type="danger">
      {{ systemStore.lastError }}
    </ElText>
  </ElCard>
</template>
