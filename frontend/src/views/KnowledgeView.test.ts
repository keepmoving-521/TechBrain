import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

import KnowledgeView from "@/views/KnowledgeView.vue";

const mocks = vi.hoisted(() => ({
  getCategoryTree: vi.fn(),
  getDocuments: vi.fn(),
}));

vi.mock("@/services/categories", () => ({
  getCategoryTree: mocks.getCategoryTree,
}));

vi.mock("@/services/documents", () => ({
  getDocuments: mocks.getDocuments,
}));

const elementStubs = {
  ElAlert: { template: "<div><slot /></div>" },
  ElButton: { template: "<button><slot /></button>" },
  ElCard: { template: "<section><slot name='header' /><slot /></section>" },
  ElEmpty: {
    props: ["description"],
    template: "<div><span>{{ description }}</span><slot /></div>",
  },
  ElOption: true,
  ElPagination: {
    emits: ["current-change"],
    template: '<button class="next-page" @click="$emit(\'current-change\', 2)">下一页</button>',
  },
  ElSelect: {
    emits: ["change"],
    template:
      "<button class=\"sort-ascending\" @click=\"$emit('change', 'updated_at')\">最早更新</button>",
  },
  ElSkeleton: { template: "<div>loading</div>" },
  ElTag: { template: "<span><slot /></span>" },
  ElTree: {
    props: ["data"],
    emits: ["node-click"],
    template: `<div>
      <button
        v-for="item in data"
        :key="item.id"
        class="category-choice"
        @click="$emit('node-click', item)"
      >{{ item.name }}</button>
    </div>`,
  },
};

const categoryTree = [
  {
    id: 1,
    parent_id: null,
    name: "Python",
    slug: "python",
    path: "backend/python",
    sort_order: 0,
    status: "active",
    direct_document_count: 1,
    document_count: 1,
    children: [],
  },
  {
    id: 2,
    parent_id: null,
    name: "MySQL",
    slug: "mysql",
    path: "database/mysql",
    sort_order: 1,
    status: "active",
    direct_document_count: 1,
    document_count: 1,
    children: [],
  },
];

function documentPage(categoryId?: number, page = 1) {
  const name = categoryId === 2 ? "MySQL 索引优化" : "SQLAlchemy 加载策略";
  return {
    items: [
      {
        id: categoryId ?? 1,
        document_id: "document-id",
        title: name,
        summary: "知识摘要",
        category_id: categoryId ?? 1,
        category: categoryId === 2 ? "database/mysql" : "backend/python",
        tags: ["实践"],
        status: "published",
        visibility: "private",
        language: "zh-CN",
        created_at: "2026-06-20T10:00:00+08:00",
        updated_at: "2026-06-29T12:00:00+08:00",
        relative_path: "document.md",
      },
    ],
    pagination: {
      page,
      page_size: 12,
      total: 13,
      total_pages: 2,
      has_previous: page > 1,
      has_next: page < 2,
    },
  };
}

async function mountKnowledge(initialPath = "/knowledge") {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/knowledge", name: "knowledge", component: KnowledgeView },
      { path: "/system/sync", component: { template: "<div />" } },
    ],
  });
  await router.push(initialPath);
  await router.isReady();
  const wrapper = mount(KnowledgeView, {
    global: { plugins: [router], stubs: elementStubs },
  });
  await flushPromises();
  return { router, wrapper };
}

describe("KnowledgeView", () => {
  beforeEach(() => {
    mocks.getCategoryTree.mockReset();
    mocks.getDocuments.mockReset();
    mocks.getCategoryTree.mockResolvedValue(categoryTree);
    mocks.getDocuments.mockImplementation((params: { category_id?: number; page: number }) =>
      Promise.resolve(documentPage(params.category_id, params.page)),
    );
  });

  it("loads the URL category and refreshes documents when category changes", async () => {
    const { router, wrapper } = await mountKnowledge("/knowledge?category_id=1");

    expect(mocks.getDocuments).toHaveBeenLastCalledWith({
      page: 1,
      page_size: 12,
      category_id: 1,
      sort: "-updated_at",
    });
    expect(wrapper.text()).toContain("SQLAlchemy 加载策略");

    await wrapper.findAll(".category-choice")[1].trigger("click");
    await flushPromises();

    expect(router.currentRoute.value.query.category_id).toBe("2");
    expect(mocks.getDocuments).toHaveBeenLastCalledWith({
      page: 1,
      page_size: 12,
      category_id: 2,
      sort: "-updated_at",
    });
    expect(wrapper.text()).toContain("MySQL 索引优化");
  });

  it("keeps pagination and sorting in the route and reloads the list", async () => {
    const { router, wrapper } = await mountKnowledge("/knowledge?category_id=1");

    await wrapper.get(".next-page").trigger("click");
    await flushPromises();
    expect(router.currentRoute.value.query.page).toBe("2");
    expect(mocks.getDocuments).toHaveBeenLastCalledWith(
      expect.objectContaining({ page: 2, sort: "-updated_at" }),
    );

    await wrapper.get(".sort-ascending").trigger("click");
    await flushPromises();
    expect(router.currentRoute.value.query.page).toBeUndefined();
    expect(router.currentRoute.value.query.sort).toBe("updated_at");
    expect(mocks.getDocuments).toHaveBeenLastCalledWith(
      expect.objectContaining({ page: 1, sort: "updated_at" }),
    );
  });

  it("shows an actionable empty state for an empty knowledge base", async () => {
    mocks.getCategoryTree.mockResolvedValue([]);
    mocks.getDocuments.mockResolvedValue({
      items: [],
      pagination: {
        page: 1,
        page_size: 12,
        total: 0,
        total_pages: 0,
        has_previous: false,
        has_next: false,
      },
    });

    const { wrapper } = await mountKnowledge();

    expect(wrapper.text()).toContain("知识库暂无可浏览文档");
    expect(wrapper.get('a[href="/system/sync"]')).toBeTruthy();
  });
});
