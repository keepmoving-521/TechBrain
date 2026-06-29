<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import {
  getKnowledgeOverview,
  type KnowledgeOverview,
  type OverviewStatistics,
} from "@/services/knowledgeOverview";

const loading = ref(true);
const loadFailed = ref(false);
const overview = ref<KnowledgeOverview | null>(null);

const emptyStatistics: OverviewStatistics = {
  document_count: 0,
  published_document_count: 0,
  draft_document_count: 0,
  category_count: 0,
  tag_count: 0,
};

const statistics = computed(() => overview.value?.statistics ?? emptyStatistics);
const statisticCards = computed(() => [
  {
    label: "知识文档",
    value: statistics.value.document_count,
    note: `${statistics.value.draft_document_count} 篇草稿`,
  },
  {
    label: "可浏览文档",
    value: statistics.value.published_document_count,
    note: "已发布及已弃用",
  },
  { label: "知识分类", value: statistics.value.category_count, note: "启用中的分类" },
  { label: "知识标签", value: statistics.value.tag_count, note: "启用中的标签" },
]);

async function loadOverview(): Promise<void> {
  loading.value = true;
  loadFailed.value = false;
  try {
    overview.value = await getKnowledgeOverview();
  } catch {
    loadFailed.value = true;
  } finally {
    loading.value = false;
  }
}

function formatUpdatedAt(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

onMounted(loadOverview);
</script>

<template>
  <ElSkeleton v-if="loading" :rows="8" animated class="overview-skeleton" />

  <ElAlert
    v-else-if="loadFailed"
    title="知识首页加载失败"
    description="请确认后端服务和数据库状态后重试。"
    type="error"
    show-icon
    :closable="false"
  >
    <template #default>
      <ElButton type="primary" @click="loadOverview">重新加载</ElButton>
    </template>
  </ElAlert>

  <section v-else-if="overview?.is_empty" class="empty-overview">
    <ElEmpty description="知识库还是空的，从同步第一篇 Markdown 开始吧。">
      <RouterLink to="/system/sync">
        <ElButton type="primary" size="large">前往同步管理</ElButton>
      </RouterLink>
    </ElEmpty>
    <p>Markdown 是唯一事实来源；同步完成后，知识总览、最近更新和常用入口会自动生成。</p>
  </section>

  <div v-else-if="overview" class="knowledge-overview">
    <section class="overview-heading">
      <div>
        <p class="eyebrow">Knowledge at a glance</p>
        <h2>今天，从已有知识继续生长</h2>
        <p>快速回到最近更新的内容，或从常用分类与标签继续探索。</p>
      </div>
      <RouterLink to="/knowledge">
        <ElButton type="primary">浏览全部知识</ElButton>
      </RouterLink>
    </section>

    <section class="statistics-grid" aria-label="知识统计">
      <ElCard v-for="item in statisticCards" :key="item.label" shadow="never" class="stat-card">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
        <small>{{ item.note }}</small>
      </ElCard>
    </section>

    <section class="overview-content-grid">
      <ElCard shadow="never" class="content-card recent-card">
        <template #header>
          <div class="card-header">
            <span>最近更新</span>
            <RouterLink to="/knowledge">查看全部</RouterLink>
          </div>
        </template>

        <div v-if="overview.recent_documents.length" class="recent-list">
          <RouterLink
            v-for="document in overview.recent_documents"
            :key="document.id"
            :to="{ name: 'knowledge', query: { document_id: document.id } }"
            class="recent-item"
          >
            <div>
              <strong>{{ document.title }}</strong>
              <p>{{ document.summary || "暂无摘要" }}</p>
              <span>{{ document.category }}</span>
            </div>
            <time :datetime="document.updated_at">{{ formatUpdatedAt(document.updated_at) }}</time>
          </RouterLink>
        </div>
        <ElEmpty v-else description="暂无可浏览的最近更新" :image-size="80" />
      </ElCard>

      <div class="entry-column">
        <ElCard shadow="never" class="content-card entry-card">
          <template #header>
            <div class="card-header"><span>常用分类</span></div>
          </template>
          <div v-if="overview.popular_categories.length" class="entry-list">
            <RouterLink
              v-for="category in overview.popular_categories"
              :key="category.id"
              :to="{ name: 'knowledge', query: { category_id: category.id } }"
            >
              <span>{{ category.name }}</span>
              <small>{{ category.document_count }} 篇</small>
            </RouterLink>
          </div>
          <ElEmpty v-else description="暂无常用分类" :image-size="60" />
        </ElCard>

        <ElCard shadow="never" class="content-card entry-card">
          <template #header>
            <div class="card-header"><span>常用标签</span></div>
          </template>
          <div v-if="overview.popular_tags.length" class="tag-list">
            <RouterLink
              v-for="tag in overview.popular_tags"
              :key="tag.id"
              :to="{ name: 'knowledge', query: { tag_id: tag.id } }"
            >
              # {{ tag.name }}
              <small>{{ tag.usage_count }}</small>
            </RouterLink>
          </div>
          <ElEmpty v-else description="暂无常用标签" :image-size="60" />
        </ElCard>
      </div>
    </section>
  </div>
</template>

<style scoped>
.overview-skeleton,
.empty-overview {
  padding: 40px;
  background: var(--tb-surface);
  border: 1px solid var(--tb-border);
  border-radius: var(--tb-radius);
}

.empty-overview {
  text-align: center;
}

.empty-overview > p {
  margin: -10px auto 18px;
  color: var(--tb-muted);
}

.knowledge-overview {
  display: grid;
  gap: 20px;
}

.overview-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 28px 32px;
  background: linear-gradient(120deg, #fff, #f0f5ff);
  border: 1px solid var(--tb-border);
  border-radius: var(--tb-radius);
}

.overview-heading h2 {
  margin: 8px 0;
  font-size: 28px;
}

.overview-heading p:last-child {
  margin: 0;
  color: var(--tb-muted);
}

.statistics-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.stat-card span,
.stat-card strong,
.stat-card small {
  display: block;
}

.stat-card span,
.stat-card small {
  color: var(--tb-muted);
}

.stat-card strong {
  margin: 10px 0 6px;
  font-size: 30px;
}

.overview-content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.8fr) minmax(300px, 1fr);
  gap: 18px;
}

.card-header a {
  font-size: 13px;
  font-weight: 500;
  color: var(--tb-primary);
}

.recent-list,
.entry-column {
  display: grid;
  gap: 14px;
}

.recent-item {
  display: flex;
  gap: 20px;
  align-items: flex-start;
  justify-content: space-between;
  padding: 14px 2px;
  border-bottom: 1px solid var(--tb-border);
}

.recent-item:last-child {
  border-bottom: 0;
}

.recent-item strong,
.recent-item p,
.recent-item span {
  display: block;
}

.recent-item p {
  margin: 6px 0;
  color: var(--tb-muted);
}

.recent-item span,
.recent-item time {
  font-size: 12px;
  color: var(--tb-muted);
}

.recent-item time {
  white-space: nowrap;
}

.entry-list {
  display: grid;
  gap: 4px;
}

.entry-list a {
  display: flex;
  justify-content: space-between;
  padding: 10px 8px;
  border-radius: 8px;
}

.entry-list a:hover,
.tag-list a:hover {
  color: var(--tb-primary);
  background: #f3f6ff;
}

.entry-list small {
  color: var(--tb-muted);
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.tag-list a {
  padding: 7px 10px;
  color: var(--tb-primary-dark);
  background: #f6f8ff;
  border-radius: 999px;
}

.tag-list small {
  margin-left: 5px;
  color: var(--tb-muted);
}
</style>
