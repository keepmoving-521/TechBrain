# 分类查询接口说明

本文档对应 TB-V10-017：实现分类查询。

## 1. 接口范围

分类查询提供两个只读接口：

```http
GET /api/v1/categories/tree
GET /api/v1/categories/{category_id}
```

接口读取 `knowledge_categories` 分类树，并基于 `knowledge_documents.category_id` 统计文档数量。

## 2. 文档数量口径

每个分类返回两种文档数量：

| 字段 | 含义 |
| --- | --- |
| `direct_document_count` | 直接归属于当前分类的未删除文档数量 |
| `document_count` | 当前分类及所有后代分类的未删除文档总数 |

软删除文档不计入数量。文档的 `published`、`draft`、`archived`、`deprecated` 状态不改变分类归属，因此只要未被软删除，均计入分类数量。

## 3. 分类树接口

### 请求

```http
GET /api/v1/categories/tree
```

### 响应示例

```json
{
  "items": [
    {
      "id": 1,
      "parent_id": null,
      "name": "backend",
      "slug": "backend",
      "path": "backend",
      "sort_order": 10,
      "status": "active",
      "direct_document_count": 1,
      "document_count": 3,
      "children": [
        {
          "id": 2,
          "parent_id": 1,
          "name": "python",
          "slug": "python",
          "path": "backend/python",
          "sort_order": 10,
          "status": "active",
          "direct_document_count": 2,
          "document_count": 2,
          "children": []
        }
      ]
    }
  ]
}
```

树接口返回所有分类，包括没有文档的空分类。没有根分类时返回：

```json
{
  "items": []
}
```

## 4. 分类详情接口

### 请求

```http
GET /api/v1/categories/2
```

### 响应说明

详情包含分类基础字段、两种文档数量、直属父分类和直属子分类。`parent` 和 `children` 中也包含文档数量，便于页面展示上下级导航。

```json
{
  "id": 2,
  "parent_id": 1,
  "name": "python",
  "slug": "python",
  "path": "backend/python",
  "sort_order": 10,
  "status": "active",
  "direct_document_count": 2,
  "document_count": 2,
  "parent": {
    "id": 1,
    "parent_id": null,
    "name": "backend",
    "slug": "backend",
    "path": "backend",
    "sort_order": 10,
    "status": "active",
    "direct_document_count": 1,
    "document_count": 3
  },
  "children": []
}
```

空分类正常返回 `200 OK`，数量为 `0`，子分类数组为空。分类不存在时返回统一错误：

```json
{
  "error": {
    "code": "HTTP_404",
    "message": "分类不存在",
    "details": null
  },
  "request_id": "..."
}
```

## 5. 排序规则

根分类和每一级子分类均使用相同的稳定排序：

```text
sort_order 升序
id 升序
```

当多个分类的 `sort_order` 相同时，使用数据库主键 `id` 保证响应顺序稳定。

## 6. 查询策略

每次查询批量加载分类和直属文档计数，再在内存中构建树并汇总后代文档数量，避免对每个分类分别执行查询造成 N+1 问题。

当前接口返回 `active`、`hidden`、`archived` 全部分类，分类状态由调用方决定展示方式。后续如果需要面向普通用户隐藏分类，应新增明确的过滤参数或独立接口，不改变当前管理查询语义。

## 7. 验收结论

TB-V10-017 已覆盖：

- 分类树层级与父子关系准确。
- 根分类和各级子分类排序稳定。
- 直属文档数量和包含后代的总数量准确。
- 软删除文档不计入分类统计。
- 空分类可在树和详情中正常展示。
- 分类详情包含父分类、直属子分类和文档数量。
- 不存在的分类返回统一 `404` 错误。
