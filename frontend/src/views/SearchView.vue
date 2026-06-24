<script setup lang="ts">
import { ref } from "vue";

const keyword = ref("");
</script>

<template>
  <ElCard shadow="never" class="content-card">
    <template #header>
      <div class="card-header">
        <span>全文检索</span>
        <ElTag type="info">ElasticSearch 接入后启用</ElTag>
      </div>
    </template>

    <ElInput
      v-model="keyword"
      size="large"
      placeholder="搜索 Python、MySQL、RAG、性能优化……"
      clearable
    />
    <ElEmpty class="placeholder-empty" description="搜索服务将在 V1.0 检索能力完成后接入。" />
  </ElCard>
</template>
