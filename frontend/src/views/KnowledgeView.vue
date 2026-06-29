<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter, type LocationQueryRaw } from "vue-router";

import { getCategoryTree, type CategoryTreeNode } from "@/services/categories";
import {
  getDocuments,
  type DocumentListItem,
  type DocumentPage,
  type DocumentSort,
} from "@/services/documents";

const PAGE_SIZE = 12;
const DEFAULT_SORT: DocumentSort = "-updated_at";

const route = useRoute();
const router = useRouter();
const categories = ref<CategoryTreeNode[]>([]);
const categoryLoading = ref(true);
const categoryFailed = ref(false);
const documents = ref<DocumentListItem[]>([]);
const pagination = ref<DocumentPage["pagination"]>({
  page: 1,
  page_size: PAGE_SIZE,
  total: 0,
  total_pages: 0,
  has_previous: false,
  has_next: false,
});
const documentLoading = ref(true);
const documentFailed = ref(false);
let requestSequence = 0;

const selectedCategoryId = computed(() => parsePositiveInteger(route.query.category_id));
const currentPage = computed(() => parsePositiveInteger(route.query.page) ?? 1);
const currentSort = computed<DocumentSort>(() =>
  route.query.sort === "updated_at" ? "updated_at" : DEFAULT_SORT,
);
const selectedCategory = computed(() => findCategory(categories.value, selectedCategoryId.value));
const pageTitle = computed(() => selectedCategory.value?.name ?? "全部知识");

async function loadCategories(): Promise<void> {
  categoryLoading.value = true;
  categoryFailed.value = false;
  try {
    const items = await getCategoryTree();
    categories.value = activeCategoryTree(items);
  } catch {
    categoryFailed.value = true;
  } finally {
    categoryLoading.value = false;
  }
}

async function loadDocuments(): Promise<void> {
  const sequence = ++requestSequence;
  documentLoading.value = true;
  documentFailed.value = false;
  try {
    const result = await getDocuments({
      page: currentPage.value,
      page_size: PAGE_SIZE,
      category_id: selectedCategoryId.value ?? undefined,
      sort: currentSort.value,
    });
    if (sequence !== requestSequence) return;
    if (result.pagination.total_pages > 0 && currentPage.value > result.pagination.total_pages) {
      await updateQuery({ page: String(result.pagination.total_pages) });
      return;
    }
    documents.value = result.items;
    pagination.value = result.pagination;
  } catch {
    if (sequence === requestSequence) {
      documentFailed.value = true;
      documents.value = [];
    }
  } finally {
    if (sequence === requestSequence) documentLoading.value = false;
  }
}

async function selectCategory(categoryId: number | null): Promise<void> {
  const query: LocationQueryRaw = {
    sort: currentSort.value === DEFAULT_SORT ? undefined : currentSort.value,
    category_id: categoryId ?? undefined,
  };
  await router.push({ name: "knowledge", query });
}

async function changePage(page: number): Promise<void> {
  await updateQuery({ page: page === 1 ? undefined : String(page) });
}

async function changeSort(sort: DocumentSort): Promise<void> {
  await updateQuery({
    page: undefined,
    sort: sort === DEFAULT_SORT ? undefined : sort,
  });
}

async function updateQuery(patch: LocationQueryRaw): Promise<void> {
  await router.push({
    name: "knowledge",
    query: { ...route.query, document_id: undefined, tag_id: undefined, ...patch },
  });
}

function documentRoute(document: DocumentListItem) {
  return {
    name: "knowledge",
    query: { ...route.query, document_id: document.id },
  };
}

function activeCategoryTree(items: CategoryTreeNode[]): CategoryTreeNode[] {
  return items
    .filter((item) => item.status === "active")
    .map((item) => ({ ...item, children: activeCategoryTree(item.children) }));
}

function findCategory(
  items: CategoryTreeNode[],
  categoryId: number | null,
): CategoryTreeNode | null {
  if (categoryId === null) return null;
  for (const category of items) {
    if (category.id === categoryId) return category;
    const child = findCategory(category.children, categoryId);
    if (child) return child;
  }
  return null;
}

function parsePositiveInteger(value: unknown): number | null {
  const text = Array.isArray(value) ? value[0] : value;
  if (typeof text !== "string" || !/^\d+$/.test(text)) return null;
  const number = Number(text);
  return number > 0 ? number : null;
}

function formatUpdatedAt(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date(value));
}

watch(() => [route.query.category_id, route.query.page, route.query.sort], loadDocuments, {
  immediate: true,
});
onMounted(loadCategories);
</script>

<template>
  <div class="knowledge-browser">
    <ElCard shadow="never" class="content-card category-panel">
      <template #header>
        <div class="card-header">
          <span>知识分类</span>
          <small>{{ categories.length }} 个根分类</small>
        </div>
      </template>

      <ElSkeleton v-if="categoryLoading" :rows="6" animated />
      <ElAlert
        v-else-if="categoryFailed"
        title="分类加载失败"
        type="error"
        :closable="false"
        show-icon
      >
        <template #default><ElButton @click="loadCategories">重试</ElButton></template>
      </ElAlert>
      <template v-else>
        <button
          class="all-category"
          :class="{ 'is-active': selectedCategoryId === null }"
          type="button"
          @click="selectCategory(null)"
        >
          <span>全部知识</span>
          <small>{{ selectedCategoryId === null ? pagination.total : "" }}</small>
        </button>
        <ElTree
          v-if="categories.length"
          :data="categories"
          node-key="id"
          :current-node-key="selectedCategoryId"
          :props="{ label: 'name', children: 'children' }"
          default-expand-all
          highlight-current
          :expand-on-click-node="false"
          @node-click="selectCategory($event.id)"
        >
          <template #default="{ data }">
            <span class="category-node">
              <span>{{ data.name }}</span>
              <small>{{ data.document_count }}</small>
            </span>
          </template>
        </ElTree>
        <ElEmpty v-else description="暂无分类" :image-size="70" />
      </template>
    </ElCard>

    <ElCard shadow="never" class="content-card document-panel">
      <template #header>
        <div class="document-header">
          <div>
            <h2>{{ pageTitle }}</h2>
            <p v-if="selectedCategory">{{ selectedCategory.path }} · 直属文档</p>
            <p v-else>浏览全部已发布知识</p>
          </div>
          <ElSelect
            :model-value="currentSort"
            aria-label="文档排序"
            style="width: 150px"
            @change="changeSort"
          >
            <ElOption label="最近更新" value="-updated_at" />
            <ElOption label="最早更新" value="updated_at" />
          </ElSelect>
        </div>
      </template>

      <ElSkeleton v-if="documentLoading" :rows="8" animated />
      <ElAlert
        v-else-if="documentFailed"
        title="文档列表加载失败"
        type="error"
        :closable="false"
        show-icon
      >
        <template #default><ElButton @click="loadDocuments">重试</ElButton></template>
      </ElAlert>
      <template v-else-if="documents.length">
        <div class="document-list">
          <RouterLink
            v-for="document in documents"
            :key="document.id"
            :to="documentRoute(document)"
            class="document-item"
          >
            <div class="document-main">
              <div class="document-title">
                <h3>{{ document.title }}</h3>
                <ElTag v-if="document.status === 'deprecated'" type="warning" size="small">
                  已弃用
                </ElTag>
              </div>
              <p>{{ document.summary || "暂无摘要" }}</p>
              <div class="document-tags">
                <ElTag v-for="tag in document.tags" :key="tag" size="small" effect="plain">
                  {{ tag }}
                </ElTag>
              </div>
            </div>
            <div class="document-meta">
              <span>{{ document.category }}</span>
              <time :datetime="document.updated_at"
                >更新于 {{ formatUpdatedAt(document.updated_at) }}</time
              >
            </div>
          </RouterLink>
        </div>

        <ElPagination
          v-if="pagination.total_pages > 1"
          class="document-pagination"
          background
          layout="prev, pager, next, total"
          :current-page="pagination.page"
          :page-size="pagination.page_size"
          :total="pagination.total"
          @current-change="changePage"
        />
      </template>
      <ElEmpty
        v-else
        :description="selectedCategory ? '该分类暂无可浏览文档' : '知识库暂无可浏览文档'"
      >
        <RouterLink v-if="!selectedCategory" to="/system/sync">
          <ElButton type="primary">前往同步管理</ElButton>
        </RouterLink>
      </ElEmpty>
    </ElCard>
  </div>
</template>

<style scoped>
.knowledge-browser {
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr);
  gap: 18px;
  align-items: start;
}

.category-panel {
  position: sticky;
  top: 16px;
}

.card-header small {
  font-weight: 400;
  color: var(--tb-muted);
}

.all-category {
  display: flex;
  width: 100%;
  padding: 10px 12px;
  margin-bottom: 6px;
  font: inherit;
  color: var(--tb-text);
  cursor: pointer;
  background: transparent;
  border: 0;
  border-radius: 8px;
  justify-content: space-between;
}

.all-category:hover,
.all-category.is-active {
  color: var(--tb-primary);
  background: #f0f4ff;
}

.category-node {
  display: flex;
  width: 100%;
  padding-right: 8px;
  justify-content: space-between;
}

.category-node small,
.all-category small {
  color: var(--tb-muted);
}

.document-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.document-header h2,
.document-header p {
  margin: 0;
}

.document-header h2 {
  font-size: 20px;
}

.document-header p {
  margin-top: 5px;
  font-size: 13px;
  color: var(--tb-muted);
}

.document-list {
  display: grid;
}

.document-item {
  display: flex;
  gap: 24px;
  justify-content: space-between;
  padding: 20px 4px;
  border-bottom: 1px solid var(--tb-border);
}

.document-item:first-child {
  padding-top: 4px;
}

.document-item:hover h3 {
  color: var(--tb-primary);
}

.document-main {
  min-width: 0;
}

.document-title,
.document-tags,
.document-meta {
  display: flex;
}

.document-title {
  gap: 10px;
  align-items: center;
}

.document-title h3 {
  margin: 0;
  font-size: 17px;
}

.document-main p {
  margin: 8px 0 12px;
  color: var(--tb-muted);
}

.document-tags {
  gap: 6px;
}

.document-meta {
  flex: 0 0 170px;
  flex-direction: column;
  gap: 8px;
  align-items: flex-end;
  font-size: 12px;
  color: var(--tb-muted);
}

.document-pagination {
  justify-content: flex-end;
  margin-top: 24px;
}
</style>
