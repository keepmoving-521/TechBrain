# 分类数据模型说明

本文档对应 TB-V10-015：建立分类数据模型。

## 1. 目标

分类用于为 Markdown 知识文档提供稳定的层级组织能力。

当前阶段只建立分类结构化数据模型，不强制改变 `knowledge_documents.category` 的字符串存储方式。后续分类管理、文档分类绑定和分类同步可以在该模型基础上继续迭代。

## 2. 数据表

表名：`knowledge_categories`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `id` | integer | 是 | 分类主键 |
| `parent_id` | integer | 否 | 父分类 ID，根分类为空 |
| `name` | string(80) | 是 | 分类展示名称 |
| `slug` | string(80) | 是 | 分类路径片段 |
| `path` | string(512) | 是 | 稳定分类路径，例如 `backend/python` |
| `sort_order` | integer | 是 | 同级排序值，越小越靠前 |
| `status` | string(32) | 是 | 分类状态 |
| `created_at` | datetime | 是 | 创建时间 |
| `updated_at` | datetime | 是 | 更新时间 |

## 3. 层级结构

分类通过 `parent_id` 形成父子树。

示例：

```text
backend
  └── python
      └── sqlalchemy
```

对应路径：

```text
backend
backend/python
backend/python/sqlalchemy
```

`path` 是分类树中的稳定路径，用于：

- 快速定位分类。
- 判断祖先和后代关系。
- 支持后续 Markdown `category` 字段映射。

## 4. 排序规则

同级分类通过 `sort_order` 排序：

```text
sort_order 小的分类排在前面
sort_order 相同则按 id 稳定排序
```

## 5. 状态规则

分类状态包括：

| 状态 | 说明 |
| --- | --- |
| `active` | 正常可用 |
| `hidden` | 隐藏展示，但仍保留结构 |
| `archived` | 已归档，不建议继续新增内容 |

## 6. 名称规则

分类展示名称 `name`：

- 去除首尾空白后不能为空。
- 最大长度 80 个字符。
- 不允许包含 `/`。
- 不允许包含控制字符。

正确示例：

```text
Python
ElasticSearch
性能优化
```

错误示例：

```text
Backend/Python
Python
AI
```

上面的 `Python\nAI` 属于包含换行控制字符的非法名称。

## 7. slug 规则

分类路径片段 `slug`：

- 统一转换为小写。
- 只允许小写字母、数字和中划线。
- 不能以中划线开头。
- 不能以中划线结尾。

正确示例：

```text
python
elastic-search
rag
```

错误示例：

```text
-python
python-
python_ai
Python/AI
```

## 8. 禁止循环父子关系

分类树必须是稳定树结构，不能出现循环。

禁止示例：

```text
backend
  └── python
      └── sqlalchemy

将 backend 的父分类设置为 sqlalchemy
```

这会形成：

```text
backend → python → sqlalchemy → backend
```

当前实现提供：

- 数据库约束：禁止分类把自己设置为自己的直接父级。
- 领域校验函数：禁止将分类移动到自己的后代节点下。

## 9. 索引与约束

核心约束：

- `path` 唯一。
- 同一父级下 `slug` 唯一。
- `sort_order >= 0`。
- `status` 只能是 `active`、`hidden`、`archived`。
- `id != parent_id`。

核心索引：

- `parent_id`
- `path`
- `status`
- `parent_id + sort_order`
- `parent_id + slug`

## 10. 验收结论

TB-V10-015 已覆盖：

- 分类可形成稳定树结构。
- 支持父子层级、排序和状态。
- 禁止直接自父级，并提供循环关系检测函数。
- 分类名称和 slug 规则明确。
