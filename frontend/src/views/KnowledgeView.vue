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
import { getTag, getTags, type KnowledgeTag } from "@/services/tags";

const PAGE_SIZE = 12;
const TAG_PAGE_SIZE = 30;
const DEFAULT_SORT: DocumentSort = "-updated_at";
const ALL_DOCUMENT_STATUSES = "published,draft,archived,deprecated";

const route = useRoute();
const router = useRouter();
const categories = ref<CategoryTreeNode[]>([]);
const categoryLoading = ref(true);
const categoryFailed = ref(false);
const tags = ref<KnowledgeTag[]>([]);
const tagPagination = ref<DocumentPage["pagination"]>({
  page: 1,
  page_size: TAG_PAGE_SIZE,
  total: 0,
  total_pages: 0,
  has_previous: false,
  has_next: false,
});
const tagLoading = ref(false);
const tagFailed = ref(false);
const selectedTagDetail = ref<KnowledgeTag | null>(null);
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
let tagRequestSequence = 0;
let tagDetailSequence = 0;

const selectedCategoryId = computed(() => parsePositiveInteger(route.query.category_id));
const selectedTagId = computed(() => parsePositiveInteger(route.query.tag_id));
const browseMode = computed<"categories" | "tags">(() =>
  route.query.view === "tags" || selectedTagId.value !== null ? "tags" : "categories",
);
const currentPage = computed(() => parsePositiveInteger(route.query.page) ?? 1);
const currentTagPage = computed(() => parsePositiveInteger(route.query.tag_page) ?? 1);
const currentSort = computed<DocumentSort>(() =>
  route.query.sort === "updated_at" ? "updated_at" : DEFAULT_SORT,
);
const selectedCategory = computed(() => findCategory(categories.value, selectedCategoryId.value));
const selectedTag = computed(
  () => tags.value.find((tag) => tag.id === selectedTagId.value) ?? selectedTagDetail.value,
);
const pageTitle = computed(() => {
  if (browseMode.value === "tags")
    return selectedTag.value ? `# ${selectedTag.value.name}` : "标签知识";
  return selectedCategory.value?.name ?? "全部知识";
});

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

async function loadTags(): Promise<void> {
  if (browseMode.value !== "tags") return;
  const sequence = ++tagRequestSequence;
  tagLoading.value = true;
  tagFailed.value = false;
  try {
    const result = await getTags({
      page: currentTagPage.value,
      page_size: TAG_PAGE_SIZE,
      sort: "-usage_count",
    });
    if (sequence !== tagRequestSequence) return;
    tags.value = result.items;
    tagPagination.value = result.pagination;
  } catch {
    if (sequence === tagRequestSequence) tagFailed.value = true;
  } finally {
    if (sequence === tagRequestSequence) tagLoading.value = false;
  }
}

async function loadSelectedTag(): Promise<void> {
  const sequence = ++tagDetailSequence;
  const tagId = selectedTagId.value;
  selectedTagDetail.value = null;
  if (tagId === null) return;
  try {
    const detail = await getTag(tagId);
    if (sequence === tagDetailSequence) selectedTagDetail.value = detail;
  } catch {
    if (sequence === tagDetailSequence) selectedTagDetail.value = null;
  }
}

async function loadDocuments(): Promise<void> {
  const sequence = ++requestSequence;
  if (browseMode.value === "tags" && selectedTagId.value === null) {
    documents.value = [];
    pagination.value = emptyPagination();
    documentFailed.value = false;
    documentLoading.value = false;
    return;
  }
  documentLoading.value = true;
  documentFailed.value = false;
  try {
    const result = await getDocuments({
      page: currentPage.value,
      page_size: PAGE_SIZE,
      category_id:
        browseMode.value === "categories" ? (selectedCategoryId.value ?? undefined) : undefined,
      tag_id: browseMode.value === "tags" ? (selectedTagId.value ?? undefined) : undefined,
      status: browseMode.value === "tags" ? ALL_DOCUMENT_STATUSES : undefined,
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
    tag_id: undefined,
    tag_page: undefined,
    view: undefined,
  };
  await router.push({ name: "knowledge", query });
}

async function selectTag(tagId: number): Promise<void> {
  await router.push({
    name: "knowledge",
    query: {
      view: "tags",
      tag_id: tagId,
      tag_page: currentTagPage.value === 1 ? undefined : currentTagPage.value,
      sort: currentSort.value === DEFAULT_SORT ? undefined : currentSort.value,
    },
  });
}

async function changeBrowseMode(mode: "categories" | "tags"): Promise<void> {
  if (mode === "categories") {
    await selectCategory(null);
    return;
  }
  await router.push({
    name: "knowledge",
    query: {
      view: "tags",
      sort: currentSort.value === DEFAULT_SORT ? undefined : currentSort.value,
    },
  });
}

async function changeTagPage(page: number): Promise<void> {
  await updateQuery({ tag_page: page === 1 ? undefined : String(page) });
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
    query: { ...route.query, document_id: undefined, ...patch },
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

function emptyPagination(): DocumentPage["pagination"] {
  return {
    page: 1,
    page_size: PAGE_SIZE,
    total: 0,
    total_pages: 0,
    has_previous: false,
    has_next: false,
  };
}

function statusLabel(status: string): string {
  return (
    {
      draft: "草稿",
      archived: "已归档",
      deprecated: "已弃用",
    }[status] ?? status
  );
}

function statusType(status: string): "info" | "warning" | "danger" {
  if (status === "draft") return "info";
  if (status === "archived") return "danger";
  return "warning";
}

function formatUpdatedAt(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date(value));
}

watch(
  () => [
    route.query.category_id,
    route.query.tag_id,
    route.query.view,
    route.query.page,
    route.query.sort,
  ],
  loadDocuments,
  { immediate: true },
);
watch(() => [browseMode.value, route.query.tag_page], loadTags, { immediate: true });
watch(selectedTagId, loadSelectedTag, { immediate: true });
onMounted(loadCategories);
</script>

<template>
  <div class="knowledge-browser">
    <ElCard shadow="never" class="content-card browse-panel">
      <template #header>
        <div class="browse-tabs" aria-label="知识浏览方式">
          <button
            type="button"
            :class="{ 'is-active': browseMode === 'categories' }"
            @click="changeBrowseMode('categories')"
          >
            分类
          </button>
          <button
            type="button"
            :class="{ 'is-active': browseMode === 'tags' }"
            @click="changeBrowseMode('tags')"
          >
            标签
          </button>
        </div>
      </template>

      <template v-if="browseMode === 'categories'">
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
      </template>

      <template v-else>
        <ElSkeleton v-if="tagLoading" :rows="8" animated />
        <ElAlert
          v-else-if="tagFailed"
          title="标签加载失败"
          type="error"
          :closable="false"
          show-icon
        >
          <template #default><ElButton @click="loadTags">重试</ElButton></template>
        </ElAlert>
        <template v-else-if="tags.length">
          <div class="tag-browser-list">
            <button
              v-for="tag in tags"
              :key="tag.id"
              type="button"
              :class="{ 'is-active': selectedTagId === tag.id }"
              @click="selectTag(tag.id)"
            >
              <span># {{ tag.name }}</span>
              <small>{{ tag.usage_count }}</small>
            </button>
          </div>
          <ElPagination
            v-if="tagPagination.total_pages > 1"
            class="tag-pagination"
            small
            layout="prev, pager, next"
            :current-page="tagPagination.page"
            :page-size="tagPagination.page_size"
            :total="tagPagination.total"
            @current-change="changeTagPage"
          />
        </template>
        <ElEmpty v-else description="暂无标签" :image-size="70" />
      </template>
    </ElCard>

    <ElCard shadow="never" class="content-card document-panel">
      <template #header>
        <div class="document-header">
          <div>
            <h2>{{ pageTitle }}</h2>
            <p v-if="browseMode === 'tags' && selectedTag">
              {{ selectedTag.usage_count }} 篇关联文档 · 包含草稿与归档
            </p>
            <p v-else-if="browseMode === 'tags'">选择左侧标签查看关联文档</p>
            <p v-else-if="selectedCategory">{{ selectedCategory.path }} · 直属文档</p>
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
                <ElTag
                  v-if="document.status !== 'published'"
                  :type="statusType(document.status)"
                  size="small"
                >
                  {{ statusLabel(document.status) }}
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
        :description="
          browseMode === 'tags'
            ? selectedTagId
              ? '该标签暂无关联文档'
              : '请选择标签查看关联文档'
            : selectedCategory
              ? '该分类暂无可浏览文档'
              : '知识库暂无可浏览文档'
        "
      >
        <RouterLink v-if="browseMode === 'categories' && !selectedCategory" to="/system/sync">
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

.browse-panel {
  position: sticky;
  top: 16px;
}

.browse-tabs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
  padding: 4px;
  background: #f1f3f8;
  border-radius: 10px;
}

.browse-tabs button {
  padding: 7px;
  font: inherit;
  color: var(--tb-muted);
  cursor: pointer;
  background: transparent;
  border: 0;
  border-radius: 7px;
}

.browse-tabs button.is-active {
  font-weight: 600;
  color: var(--tb-primary);
  background: #fff;
  box-shadow: 0 3px 10px rgb(16 24 39 / 8%);
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

.tag-browser-list {
  display: grid;
  gap: 4px;
}

.tag-browser-list button {
  display: flex;
  justify-content: space-between;
  padding: 9px 11px;
  font: inherit;
  color: var(--tb-text);
  cursor: pointer;
  background: transparent;
  border: 0;
  border-radius: 8px;
}

.tag-browser-list button:hover,
.tag-browser-list button.is-active {
  color: var(--tb-primary);
  background: #f0f4ff;
}

.tag-browser-list small {
  color: var(--tb-muted);
}

.tag-pagination {
  justify-content: center;
  margin-top: 14px;
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
