# 文档列表接口说明

本文档对应 TB-V10-025：实现文档列表接口。

## 1. 接口

```http
GET /api/v1/documents
```

接口提供分页文档列表，支持分类、标签、状态、源更新时间范围过滤，以及源更新时间升降序排列。

## 2. 查询参数

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `page` | integer | `1` | 页码，从 1 开始 |
| `page_size` | integer | `20` | 每页数量，范围 1 到 100 |
| `category_id` | integer | 无 | 按直属分类 ID 过滤 |
| `tag_id` | integer | 无 | 按结构化标签关联过滤 |
| `status` | string | 无 | 逗号分隔的文档状态 |
| `updated_from` | datetime | 无 | 源更新时间下界，包含边界 |
| `updated_to` | datetime | 无 | 源更新时间上界，包含边界 |
| `sort` | enum | `-updated_at` | 更新时间排序方式 |

支持的状态：

```text
published
draft
archived
deprecated
```

多状态示例：

```http
GET /api/v1/documents?status=published,deprecated
```

排序：

| `sort` | 说明 |
| --- | --- |
| `updated_at` | 按 Markdown 源更新时间升序 |
| `-updated_at` | 按 Markdown 源更新时间降序，默认值 |

## 3. 默认可见性规则

未传 `status` 时，普通列表只返回：

```text
published
deprecated
```

默认隐藏：

- `draft`：草稿不进入普通知识列表。
- `archived`：归档内容不进入普通知识列表。

如需查看草稿或归档，必须显式传入状态：

```http
GET /api/v1/documents?status=draft
GET /api/v1/documents?status=archived
GET /api/v1/documents?status=draft,archived
```

软删除文档在任何状态过滤下都不会返回。即使请求 `status=published,draft,archived,deprecated`，`is_deleted=true` 的文档仍被强制排除。

## 4. 分类与标签过滤

### 分类

```http
GET /api/v1/documents?category_id=10
```

分类过滤匹配文档的直属 `category_id`，不自动包含子分类。这使查询语义明确，分类页面如需展示整棵子树，应先取得子分类 ID 后显式组合，或由后续需求增加 `include_descendants` 参数。

### 标签

```http
GET /api/v1/documents?tag_id=20
```

标签过滤使用 `knowledge_document_tags` 结构化关联，而不是 JSON 字符串匹配，因此不会产生大小写或局部文本误匹配。

分类、标签、状态和时间范围可以组合使用，所有条件之间为逻辑 AND。

## 5. 更新时间范围

```http
GET /api/v1/documents?updated_from=2026-06-01T00:00:00%2B08:00&updated_to=2026-06-30T23:59:59%2B08:00
```

响应中的 `updated_at` 和过滤字段均对应 Markdown Front Matter 的 `updated_at`，即数据库 `source_updated_at`，不是数据库记录自身的更新时间。

规则：

- 时间必须是 ISO 8601 格式。
- 建议包含时区偏移。
- 下界和上界均为包含关系。
- `updated_from` 晚于 `updated_to` 时返回 `400`。

## 6. 稳定排序

排序始终追加数据库文档 ID：

```text
updated_at 升序  → source_updated_at ASC, id ASC
updated_at 降序  → source_updated_at DESC, id DESC
```

即使多篇文档具有相同更新时间，跨页查询顺序仍保持稳定。

## 7. 响应示例

```json
{
  "items": [
    {
      "id": 12,
      "document_id": "sqlalchemy-joinedload",
      "title": "SQLAlchemy joinedload 使用指南",
      "summary": "SQLAlchemy 关联加载实践。",
      "category_id": 3,
      "category": "backend/python",
      "tags": ["orm", "sqlalchemy"],
      "status": "published",
      "visibility": "private",
      "language": "zh-CN",
      "created_at": "2026-06-20T10:00:00+08:00",
      "updated_at": "2026-06-29T12:00:00+08:00",
      "relative_path": "backend/python/sqlalchemy-joinedload.md"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 1,
    "total_pages": 1,
    "has_previous": false,
    "has_next": false
  }
}
```

`created_at`、`updated_at` 分别映射 Markdown Front Matter 的创建和更新时间。

## 8. 空列表与错误

没有匹配文档时返回 `200 OK`：

```json
{
  "items": [],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 0,
    "total_pages": 0,
    "has_previous": false,
    "has_next": false
  }
}
```

错误场景：

| 状态码 | 场景 |
| --- | --- |
| `400` | 状态值不支持、状态集合为空、时间范围反转 |
| `422` | 页码、每页数量、ID、时间格式或排序值不合法 |

不存在的分类或标签 ID 返回空列表，而不是 `404`，便于筛选页面统一处理已失效条件。

## 9. 验收结论

TB-V10-025 已覆盖：

- 提供符合 API 规范的分页文档列表。
- 支持分类、标签、状态和源更新时间范围组合过滤。
- 支持更新时间升序和降序。
- 相同更新时间使用文档 ID 保证稳定排序。
- 默认隐藏草稿和归档内容。
- 显式状态过滤可以查询草稿和归档。
- 软删除文档始终排除。
- 分页总数、总页数和前后页标识准确。
