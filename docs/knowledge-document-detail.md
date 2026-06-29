# 文档详情接口说明

本文档对应 TB-V10-029：实现文档详情接口。

## 1. 接口

```http
GET /api/v1/documents/{id}
```

路径参数 `id` 是 `knowledge_documents.id` 数据库主键，必须为正整数。响应中的 `document_id` 是 Markdown Front Matter 提供的稳定文档身份，两者含义不同。

知识首页及知识列表使用数据库主键构造详情入口；源文件移动不会改变数据库记录或 Front Matter `document_id`。

## 2. 响应内容

接口返回未软删除文档的完整读取模型：

| 数据组 | 字段 |
| --- | --- |
| 身份 | `id`、`document_id` |
| 内容 | `title`、`summary`、`body` |
| 分类与标签 | `category_id`、`category`、`tags`、`aliases` |
| Front Matter | `status`、`visibility`、`language`、`source`、`created_at`、`updated_at` |
| 源文件 | `relative_path` |
| 同步信息 | `sync.status`、`sync.error`、扫描与同步时间、三个完整性哈希 |
| 记录时间 | `record_created_at`、`record_updated_at` |

`body` 是不包含 Front Matter 的 Markdown 正文。`created_at` 和 `updated_at` 对应 Markdown 源时间；`record_created_at` 和 `record_updated_at` 对应数据库记录时间。

出于本机路径隐私考虑，接口只返回知识库内的 `relative_path`，不返回 `absolute_path`。

## 3. 响应示例

```json
{
  "id": 12,
  "document_id": "sqlalchemy-loading",
  "title": "SQLAlchemy 加载策略",
  "summary": "理解 joinedload 与 contains_eager。",
  "body": "# SQLAlchemy 加载策略\n\n正文……",
  "category_id": 3,
  "category": "backend/python",
  "tags": ["ORM", "SQLAlchemy"],
  "aliases": ["joinedload"],
  "status": "published",
  "visibility": "private",
  "language": "zh-CN",
  "source": {"type": "summary"},
  "relative_path": "backend/python/sqlalchemy-loading.md",
  "created_at": "2026-06-20T10:00:00+08:00",
  "updated_at": "2026-06-29T12:00:00+08:00",
  "sync": {
    "status": "synced",
    "error": null,
    "last_scanned_at": "2026-06-29T12:01:00+08:00",
    "last_synced_at": "2026-06-29T12:01:00+08:00",
    "path_hash": "...",
    "content_hash": "...",
    "front_matter_hash": "..."
  },
  "record_created_at": "2026-06-29T12:01:00+08:00",
  "record_updated_at": "2026-06-29T12:01:00+08:00"
}
```

## 4. 状态与错误

| HTTP 状态 | 场景 | 错误消息 |
| --- | --- | --- |
| `200 OK` | 文档存在且未软删除 | 返回完整详情 |
| `404 Not Found` | 主键不存在 | `文档不存在` |
| `410 Gone` | 文档已软删除 | `文档已删除` |
| `422 Unprocessable Content` | ID 不是正整数 | 统一参数校验错误 |

软删除文档不会返回正文或元数据。使用 `410 Gone` 与从未存在的文档区分，也为后续恢复提示保留明确语义。

## 5. 验收结论

- 有效文档返回正文、Front Matter 元数据、分类标签、源路径和同步信息。
- Markdown 源时间与数据库记录时间语义明确。
- 不泄露本机绝对路径。
- 不存在文档返回统一 `404`。
- 软删除文档返回统一 `410`，且不返回已删除内容。
- 非法 ID 返回统一 `422` 参数校验响应。
