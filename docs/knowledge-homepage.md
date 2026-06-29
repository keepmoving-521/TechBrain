# TechBrain 知识首页

## 1. 目标

TB-V10-026 将根路由 `/` 建设为知识首页，集中展示知识统计、最近更新、常用分类与常用标签，并为尚未同步文档的知识库提供初始化引导。

## 2. 首页接口

```http
GET /api/v1/knowledge/overview
```

响应包含：

- `is_empty`：不存在任何未删除文档时为 `true`。
- `statistics`：未删除文档、可浏览文档、草稿、启用分类及启用标签数量。
- `recent_documents`：最近更新的 6 篇可浏览文档。
- `popular_categories`：按直接关联文档数排序的 6 个启用分类。
- `popular_tags`：按文档使用次数排序的 6 个启用标签。

示例：

```json
{
  "is_empty": false,
  "statistics": {
    "document_count": 12,
    "published_document_count": 9,
    "draft_document_count": 2,
    "category_count": 6,
    "tag_count": 18
  },
  "recent_documents": [],
  "popular_categories": [],
  "popular_tags": []
}
```

## 3. 数据口径

- 文档总数统计所有未软删除文档；归档文档包含在总数中，但不会作为首页浏览入口。
- 可浏览内容只包括 `published` 和 `deprecated`，排除草稿、归档及软删除文档。
- 分类和标签总数只统计 `active` 状态。
- 常用分类使用文档的直接分类关联计数，不递归累加子分类，避免同一文档在层级中重复贡献热度。
- 数量相同时使用稳定的名称、排序值或主键排序，保证刷新结果一致。

## 4. 页面导航

- 最近文档跳转至 `/knowledge?document_id={id}`。
- 常用分类跳转至 `/knowledge?category_id={id}`。
- 常用标签跳转至 `/knowledge?tag_id={id}`。
- 空知识库引导跳转至 `/system/sync`，用于发起首次 Markdown 同步。

## 5. 验收检查

```powershell
cd backend
python -m pytest tests/test_knowledge_overview_api.py

cd ..\frontend
npm.cmd test -- DashboardView.test.ts
```

接口测试覆盖空知识库、统计口径、内容过滤与稳定排序；页面测试覆盖数据展示、空状态及各类入口的目标路由。
