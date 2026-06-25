# TechBrain API 基础规范

## 1. 文档目的

本文定义 TechBrain 后续 API 开发必须遵守的基础规范，覆盖请求、响应、分页、错误码、时间格式和接口版本规则。

适用范围：

- 后端 REST JSON API。
- 前端调用后端接口。
- 后续 OpenAPI、接口测试和前端类型生成。
- V2.0 之后的 AI 流式接口在 REST 基础上扩展 SSE 规范。

## 2. 基础约定

### 2.1 协议与数据格式

- API 使用 HTTP/HTTPS。
- 默认请求与响应格式为 JSON。
- 请求头应包含：

```http
Accept: application/json
Content-Type: application/json
```

- 响应 JSON 字段使用 `snake_case`。
- 布尔值使用 JSON 原生 `true` / `false`。
- 空值使用 JSON 原生 `null`，不要用空字符串表达不存在。
- 金额、计数、分页数量等数值字段使用 JSON number。
- ID 字段默认使用字符串，避免前端大整数精度问题。

### 2.2 字段命名

| 类型 | 规范 | 示例 |
| --- | --- | --- |
| JSON 字段 | `snake_case` | `created_at` |
| HTTP Header | `Title-Case` | `X-Request-ID` |
| Query 参数 | `snake_case` | `page_size` |
| 枚举值 | 小写字符串，必要时使用下划线 | `published`、`sync_failed` |
| 错误码 | 大写下划线 | `VALIDATION_ERROR` |

## 3. 接口版本规范

所有正式业务接口必须带版本前缀：

```text
/api/v1
```

示例：

```http
GET /api/v1/health/live
GET /api/v1/documents
POST /api/v1/sync-jobs
```

版本规则：

- `v1` 内允许新增接口、新增可选字段、新增枚举值。
- `v1` 内不允许删除字段、修改字段含义、修改成功响应结构。
- 破坏性变更必须进入新版本，例如 `/api/v2`。
- 废弃接口应先在文档中标记 deprecated，再保留至少一个大版本周期。

## 4. 请求规范

### 4.1 请求 ID

客户端可以传入请求 ID：

```http
X-Request-ID: d5315d67361b4e24a337081b64cdf80e
```

规则：

- 请求 ID 用于日志关联和问题排查。
- 如果客户端未传入，服务端自动生成。
- 如果客户端传入非法值，服务端自动替换。
- 所有响应必须返回 `X-Request-ID`。
- 错误响应体必须包含 `request_id`。

### 4.2 Query 参数

查询、过滤、分页、排序优先使用 query 参数。

示例：

```http
GET /api/v1/documents?page=1&page_size=20&category_id=python&sort=-updated_at
```

常用规则：

- 可选参数未传入时使用服务端默认值。
- 多值过滤优先使用逗号分隔字符串，例如 `tag_ids=orm,mysql`。
- 复杂查询条件如果明显超过 URL 可读性，可使用 `POST /search` 类接口。

### 4.3 请求体

创建和更新资源使用 JSON body。

示例：

```http
POST /api/v1/categories
Content-Type: application/json
X-Request-ID: 2d9294f3d2f1435d90a48399510cc39e

{
  "name": "Python",
  "parent_id": null,
  "sort_order": 100
}
```

请求体规则：

- 不允许传入服务端生成字段，例如 `created_at`、`updated_at`。
- 更新接口优先使用局部更新语义，未传字段不修改。
- 必填字段缺失、类型错误或格式错误返回 `422 VALIDATION_ERROR`。

## 5. 响应规范

### 5.1 单对象响应

单对象接口直接返回资源对象。

示例：

```json
{
  "id": "doc_01jz2r6x0w8t9v6e4qf6kr9ndp",
  "title": "SQLAlchemy joinedload 使用笔记",
  "category_id": "python",
  "tag_ids": ["orm", "performance"],
  "status": "published",
  "created_at": "2026-06-25T10:12:30+08:00",
  "updated_at": "2026-06-25T11:03:18+08:00"
}
```

### 5.2 创建响应

资源创建成功返回 `201 Created`，响应体返回创建后的资源或创建结果。

示例：

```http
HTTP/1.1 201 Created
Location: /api/v1/categories/python
X-Request-ID: 2d9294f3d2f1435d90a48399510cc39e
```

```json
{
  "id": "python",
  "name": "Python",
  "parent_id": null,
  "sort_order": 100,
  "created_at": "2026-06-25T10:12:30+08:00",
  "updated_at": "2026-06-25T10:12:30+08:00"
}
```

### 5.3 删除响应

删除成功且无需返回内容时使用：

```http
HTTP/1.1 204 No Content
X-Request-ID: 921138d55f5041eaa0d6aa8df7aaad74
```

如果删除是异步任务，返回 `202 Accepted` 和任务信息。

### 5.4 异步任务响应

触发同步、索引重建、批量处理等异步任务时返回 `202 Accepted`。

示例：

```json
{
  "task_id": "sync_01jz2rfh6w6y1v3yxj77a5n2m6",
  "status": "pending",
  "message": "同步任务已创建",
  "created_at": "2026-06-25T10:12:30+08:00"
}
```

## 6. 分页规范

### 6.1 页码分页

V1.0 默认使用页码分页。

请求参数：

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `page` | integer | `1` | 页码，从 1 开始 |
| `page_size` | integer | `20` | 每页数量 |

约束：

- `page >= 1`
- `1 <= page_size <= 100`
- 超出范围返回 `422 VALIDATION_ERROR`

响应格式：

```json
{
  "items": [
    {
      "id": "doc_01jz2r6x0w8t9v6e4qf6kr9ndp",
      "title": "SQLAlchemy joinedload 使用笔记",
      "updated_at": "2026-06-25T11:03:18+08:00"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 135,
    "total_pages": 7,
    "has_previous": false,
    "has_next": true
  }
}
```

### 6.2 排序

排序参数统一使用 `sort`。

规则：

- 升序：`sort=created_at`
- 降序：`sort=-updated_at`
- 多字段排序：`sort=-updated_at,title`

接口必须明确支持哪些排序字段。传入不支持字段返回：

```json
{
  "error": {
    "code": "INVALID_SORT_FIELD",
    "message": "不支持的排序字段",
    "details": {
      "field": "score",
      "allowed": ["created_at", "updated_at", "title"]
    }
  },
  "request_id": "f12610d883114b728c1c56e074e5f7b8"
}
```

## 7. 时间格式规范

时间字段统一使用 ISO 8601 / RFC 3339 格式，并包含时区偏移。

示例：

```json
{
  "created_at": "2026-06-25T10:12:30+08:00",
  "updated_at": "2026-06-25T11:03:18+08:00"
}
```

规则：

- API 响应必须带时区。
- 数据库存储建议使用 UTC 或明确时区策略。
- 日期字段使用 `YYYY-MM-DD`，例如 `2026-06-25`。
- 持续时间使用秒数，字段名使用 `_seconds` 后缀。
- 不使用模糊时间字符串，例如 `刚刚`、`昨天`。

## 8. HTTP 状态码规范

| 状态码 | 使用场景 |
| --- | --- |
| `200 OK` | 查询、更新或普通操作成功 |
| `201 Created` | 同步创建资源成功 |
| `202 Accepted` | 异步任务已接受 |
| `204 No Content` | 删除成功且无响应体 |
| `400 Bad Request` | 请求语义错误，无法处理 |
| `401 Unauthorized` | 未认证 |
| `403 Forbidden` | 已认证但无权限 |
| `404 Not Found` | 资源不存在 |
| `409 Conflict` | 资源冲突或状态冲突 |
| `412 Precondition Failed` | 前置条件不满足，例如版本号冲突 |
| `422 Unprocessable Content` | 参数校验失败 |
| `429 Too Many Requests` | 请求过于频繁 |
| `500 Internal Server Error` | 服务端未知错误 |
| `503 Service Unavailable` | 依赖不可用或服务未就绪 |

## 9. 错误响应规范

所有 API 错误统一返回：

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "请求参数校验失败",
    "details": [
      {
        "field": "query.page",
        "message": "Input should be greater than or equal to 1",
        "type": "greater_than_equal"
      }
    ]
  },
  "request_id": "d5315d67361b4e24a337081b64cdf80e"
}
```

字段说明：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `error.code` | string | 稳定错误码，用于前端分支处理 |
| `error.message` | string | 可展示给用户的错误摘要 |
| `error.details` | any | 可选错误详情 |
| `request_id` | string | 请求链路 ID |

错误响应头必须包含：

```http
X-Request-ID: d5315d67361b4e24a337081b64cdf80e
```

### 9.1 通用错误码

| 错误码 | HTTP 状态码 | 说明 |
| --- | --- | --- |
| `VALIDATION_ERROR` | `422` | 请求参数校验失败 |
| `INTERNAL_SERVER_ERROR` | `500` | 服务端未知错误 |
| `HTTP_400` | `400` | 通用错误请求 |
| `HTTP_401` | `401` | 未认证 |
| `HTTP_403` | `403` | 无权限 |
| `HTTP_404` | `404` | 资源不存在 |
| `HTTP_409` | `409` | 资源冲突 |
| `HTTP_503` | `503` | 服务或依赖不可用 |
| `INVALID_SORT_FIELD` | `400` | 不支持的排序字段 |
| `RESOURCE_CONFLICT` | `409` | 资源状态冲突 |
| `RESOURCE_DELETED` | `409` | 资源已删除，不能继续操作 |
| `DEPENDENCY_UNAVAILABLE` | `503` | 下游依赖不可用 |

后续业务模块可以新增稳定业务错误码，但必须写入对应接口文档。

### 9.2 资源不存在示例

```http
HTTP/1.1 404 Not Found
X-Request-ID: not-found-test
```

```json
{
  "error": {
    "code": "HTTP_404",
    "message": "资源不存在",
    "details": null
  },
  "request_id": "not-found-test"
}
```

### 9.3 参数校验失败示例

```http
GET /api/v1/documents?page=0
```

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "请求参数校验失败",
    "details": [
      {
        "field": "query.page",
        "message": "Input should be greater than or equal to 1",
        "type": "greater_than_equal"
      }
    ]
  },
  "request_id": "91c994d9e7cb45abae4ff7c8a71bc25d"
}
```

### 9.4 未处理异常示例

```json
{
  "error": {
    "code": "INTERNAL_SERVER_ERROR",
    "message": "服务器内部错误",
    "details": null
  },
  "request_id": "unhandled-test"
}
```

服务端必须记录完整异常堆栈，客户端响应不得暴露内部堆栈、SQL、密钥、文件路径等敏感信息。

## 10. 健康检查规范

### 10.1 存活检查

```http
GET /api/v1/health/live
```

成功响应：

```json
{
  "status": "ok",
  "service": "TechBrain API",
  "version": "0.1.0",
  "environment": "local"
}
```

### 10.2 就绪检查

```http
GET /api/v1/health/ready
```

成功响应：

```json
{
  "status": "ok",
  "service": "TechBrain API",
  "version": "0.1.0",
  "environment": "local",
  "checks": [
    {
      "name": "configuration",
      "status": "ok",
      "message": null
    },
    {
      "name": "database",
      "status": "ok",
      "message": null
    }
  ]
}
```

依赖不可用时返回 `503 Service Unavailable`：

```json
{
  "status": "error",
  "service": "TechBrain API",
  "version": "0.1.0",
  "environment": "local",
  "checks": [
    {
      "name": "configuration",
      "status": "ok",
      "message": null
    },
    {
      "name": "database",
      "status": "error",
      "message": "database unavailable"
    }
  ]
}
```

## 11. REST 资源命名规范

资源路径使用复数名词。

示例：

| 操作 | 方法与路径 |
| --- | --- |
| 文档列表 | `GET /api/v1/documents` |
| 文档详情 | `GET /api/v1/documents/{document_id}` |
| 创建分类 | `POST /api/v1/categories` |
| 更新分类 | `PATCH /api/v1/categories/{category_id}` |
| 删除分类 | `DELETE /api/v1/categories/{category_id}` |
| 触发同步任务 | `POST /api/v1/sync-jobs` |
| 查看同步任务 | `GET /api/v1/sync-jobs/{sync_job_id}` |

规则：

- 路径中不使用动词，动作类能力建模为任务资源，例如 `sync-jobs`。
- 批量操作使用明确资源名，例如 `POST /api/v1/index-rebuild-jobs`。
- 嵌套路径最多两层，避免过深嵌套。

## 12. OpenAPI 规范

后端使用 FastAPI 自动生成 OpenAPI。

要求：

- 每个正式接口必须声明 `summary`。
- 请求体和响应体必须使用 Pydantic Schema。
- 典型错误响应应在接口文档中声明。
- 废弃接口必须标记 `deprecated=true`。
- 后续前端类型生成以 OpenAPI Schema 为准。

## 13. 安全与兼容性

- 不在 URL、日志、错误详情中暴露密钥和敏感路径。
- 错误响应不得包含 Python traceback。
- 接口新增字段必须保持向后兼容。
- 前端应忽略未知响应字段。
- 后端删除字段必须进入新 API 版本。

## 14. 后续接口开发检查清单

新增 API 时必须确认：

- [ ] 路径以 `/api/v1` 开头。
- [ ] 路径使用复数名词。
- [ ] 请求参数使用 `snake_case`。
- [ ] 响应字段使用 `snake_case`。
- [ ] 时间字段使用 ISO 8601 并包含时区。
- [ ] 分页接口使用统一 `items + pagination` 结构。
- [ ] 错误响应使用统一 `error + request_id` 结构。
- [ ] 响应头包含 `X-Request-ID`。
- [ ] OpenAPI `summary` 和 Schema 完整。
- [ ] 正常与异常场景均有测试覆盖。
