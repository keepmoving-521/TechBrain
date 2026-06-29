# 标签查询接口说明

本文档对应 TB-V10-022：实现标签查询。

## 1. 接口范围

标签查询提供：

```http
GET /api/v1/tags
GET /api/v1/tags/{tag_id}
GET /api/v1/tags/{tag_id}/documents
```

接口支持标签列表、标签详情、使用次数和关联文档分页查询。

## 2. 使用次数口径

`usage_count` 表示当前标签关联的未软删除文档数量。

- 正常、草稿、归档和废弃状态的文档，只要未软删除，均计入使用次数。
- 软删除文档保留标签关联，但不计入使用次数，也不出现在关联文档查询中。
- 没有关联有效文档的标签返回 `usage_count: 0`。
- `active` 和 `archived` 标签均可查询，状态不改变统计口径。

## 3. 标签列表

### 请求

```http
GET /api/v1/tags?page=1&page_size=20&sort=-usage_count
```

分页参数：

| 参数 | 默认值 | 约束 |
| --- | --- | --- |
| `page` | `1` | 大于等于 1 |
| `page_size` | `20` | 1 到 100 |

排序参数：

| `sort` | 说明 |
| --- | --- |
| `name` | 按规范化名称升序，默认值 |
| `-name` | 按规范化名称降序 |
| `usage_count` | 按使用次数升序 |
| `-usage_count` | 按使用次数降序 |

使用次数相同时按规范化名称升序、标签 ID 升序，保证结果稳定。

### 响应示例

```json
{
  "items": [
    {
      "id": 1,
      "name": "ORM",
      "normalized_name": "orm",
      "status": "active",
      "usage_count": 12,
      "created_at": "2026-06-29T10:00:00+08:00",
      "updated_at": "2026-06-29T10:00:00+08:00"
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

## 4. 标签详情

### 请求

```http
GET /api/v1/tags/1
```

### 响应示例

```json
{
  "id": 1,
  "name": "ORM",
  "normalized_name": "orm",
  "status": "active",
  "usage_count": 12,
  "created_at": "2026-06-29T10:00:00+08:00",
  "updated_at": "2026-06-29T10:00:00+08:00"
}
```

标签不存在时返回统一 `404`：

```json
{
  "error": {
    "code": "HTTP_404",
    "message": "标签不存在",
    "details": null
  },
  "request_id": "..."
}
```

## 5. 标签关联文档

### 请求

```http
GET /api/v1/tags/1/documents?page=1&page_size=20
```

文档默认按以下顺序排列：

```text
source_updated_at 降序
id 降序
```

### 响应示例

```json
{
  "items": [
    {
      "id": 10,
      "document_id": "sqlalchemy-joinedload",
      "title": "SQLAlchemy joinedload 使用指南",
      "summary": "SQLAlchemy 关联加载实践。",
      "category_id": 3,
      "category": "backend/python",
      "status": "published",
      "source_updated_at": "2026-06-29T12:00:00+08:00",
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

空标签正常返回 `200 OK`、空 `items` 和 `total: 0`。

## 6. 查询实现

使用次数通过文档标签关联表和未删除文档进行聚合，再与标签表执行外连接：

- 标签没有文档时仍可返回。
- 标签列表不会产生逐标签查询的 N+1 问题。
- 列表、详情和关联文档使用相同的软删除过滤口径。
- 文档分页先统计总数，再按稳定顺序读取当前页。

## 7. 验收结论

TB-V10-022 已覆盖：

- 支持标签分页列表和详情查询。
- 标签使用次数准确排除软删除文档。
- 空标签正常显示且使用次数为 0。
- 支持按名称和使用次数升序、降序排列。
- 排序结果具有稳定次序。
- 支持标签关联文档分页查询。
- 关联文档按源更新时间稳定倒序。
- 标签不存在和参数非法时返回统一错误。
