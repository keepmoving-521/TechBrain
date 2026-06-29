import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

import DashboardView from "@/views/DashboardView.vue";

const mocks = vi.hoisted(() => ({
  getKnowledgeOverview: vi.fn(),
}));

vi.mock("@/services/knowledgeOverview", () => ({
  getKnowledgeOverview: mocks.getKnowledgeOverview,
}));

const elementStubs = {
  ElAlert: { template: "<div><slot /></div>" },
  ElButton: { template: "<button><slot /></button>" },
  ElCard: { template: "<section><slot name='header' /><slot /></section>" },
  ElEmpty: {
    props: ["description"],
    template: "<div><span>{{ description }}</span><slot /></div>",
  },
  ElSkeleton: { template: "<div>loading</div>" },
};

async function mountDashboard() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/", component: DashboardView },
      { path: "/knowledge", name: "knowledge", component: { template: "<div />" } },
      { path: "/system/sync", component: { template: "<div />" } },
    ],
  });
  await router.push("/");
  await router.isReady();
  const wrapper = mount(DashboardView, {
    global: { plugins: [router], stubs: elementStubs },
  });
  await flushPromises();
  return wrapper;
}

describe("DashboardView", () => {
  beforeEach(() => {
    mocks.getKnowledgeOverview.mockReset();
  });

  it("renders accurate overview data and navigable knowledge entries", async () => {
    mocks.getKnowledgeOverview.mockResolvedValue({
      is_empty: false,
      statistics: {
        document_count: 8,
        published_document_count: 6,
        draft_document_count: 2,
        category_count: 4,
        tag_count: 5,
      },
      recent_documents: [
        {
          id: 7,
          document_id: "sqlalchemy-loading",
          title: "SQLAlchemy 加载策略",
          summary: "理解 joinedload 与 contains_eager。",
          category_id: 3,
          category: "backend/python",
          tags: ["ORM"],
          status: "published",
          updated_at: "2026-06-29T12:00:00+08:00",
        },
      ],
      popular_categories: [{ id: 3, name: "Python", path: "backend/python", document_count: 4 }],
      popular_tags: [{ id: 9, name: "ORM", usage_count: 3 }],
    });

    const wrapper = await mountDashboard();

    expect(wrapper.text()).toContain("知识文档8");
    expect(wrapper.text()).toContain("2 篇草稿");
    expect(wrapper.text()).toContain("SQLAlchemy 加载策略");
    expect(wrapper.text()).toContain("Python4 篇");
    expect(wrapper.text()).toContain("# ORM 3");
    const links = wrapper.findAll("a").map((link) => link.attributes("href"));
    expect(links).toContain("/knowledge?document_id=7");
    expect(links).toContain("/knowledge?category_id=3");
    expect(links).toContain("/knowledge?tag_id=9");
  });

  it("guides an empty knowledge base to synchronization", async () => {
    mocks.getKnowledgeOverview.mockResolvedValue({
      is_empty: true,
      statistics: {
        document_count: 0,
        published_document_count: 0,
        draft_document_count: 0,
        category_count: 0,
        tag_count: 0,
      },
      recent_documents: [],
      popular_categories: [],
      popular_tags: [],
    });

    const wrapper = await mountDashboard();

    expect(wrapper.text()).toContain("知识库还是空的");
    expect(wrapper.get('a[href="/system/sync"]')).toBeTruthy();
  });
});
