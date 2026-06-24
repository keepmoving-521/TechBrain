<script setup lang="ts">
const capabilityCards = [
  {
    title: "Markdown SSOT",
    description: "以 Markdown 作为唯一事实来源，后续同步到结构化存储与检索引擎。",
  },
  {
    title: "全文检索",
    description: "V1.0 接入 ElasticSearch，形成个人技术搜索引擎。",
  },
  {
    title: "RAG 问答",
    description: "V2.0 引入向量检索和 LLM，让个人知识库变成可问答助手。",
  },
];
</script>

<template>
  <section class="hero-panel">
    <div>
      <p class="eyebrow">TechBrain</p>
      <h2>面向程序员的 AI 技术知识大脑平台</h2>
      <p>
        统一沉淀学习笔记、项目经验、技术文档和 AI 生成内容，逐步构建个人技术百科、 搜索引擎、RAG
        知识库和第二大脑。
      </p>
      <div class="hero-actions">
        <ElButton type="primary" size="large" tag="router-link" to="/knowledge"
          >进入知识库</ElButton
        >
        <ElButton size="large" tag="router-link" to="/system/status">查看系统状态</ElButton>
      </div>
    </div>
  </section>

  <section class="card-grid">
    <ElCard v-for="card in capabilityCards" :key="card.title" shadow="never" class="feature-card">
      <h3>{{ card.title }}</h3>
      <p>{{ card.description }}</p>
    </ElCard>
  </section>
</template>
