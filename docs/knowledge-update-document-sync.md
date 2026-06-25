# TechBrain 修改文档同步说明

本文说明 TechBrain 如何识别已存在 Markdown 文档的变化，并更新结构化存储。

本能力对应 TB-V10-008，依赖 TB-V10-007。

## 1. 职责边界

修改文档同步负责：

- 识别已存在文档是否发生变化。
- 正文变化时更新 `body` 和 `content_hash`。
- Front Matter 变化时更新结构化元数据和 `front_matter_hash`。
- 路径哈希变化时更新路径相关字段。
- 未变化时不重复更新数据库记录。

本阶段不负责：

- 文件移动的完整识别策略。
- 源文件删除后的软删除。
- 同步历史流水表。
- 搜索索引和向量索引刷新。

## 2. 同步入口

后端提供通用同步函数：

```python
from techbrain.knowledge.sync import sync_markdown_document

result = sync_markdown_document(session, markdown_file, encoding="utf-8")
```

输出状态：

| 状态 | 说明 |
| --- | --- |
| `created` | 数据库中不存在该文档，已新增 |
| `updated` | 文档已存在且发生变化，已更新 |
| `unchanged` | 文档已存在且未变化，未更新数据库 |
| `error` | Markdown 解析失败，未写入数据库 |

`sync_new_markdown_document` 仍保留为新增文档兼容入口；需要支持修改同步时应使用 `sync_markdown_document`。

## 3. 变化识别

同步服务使用三个哈希判断变化：

| 字段 | 来源 | 含义 |
| --- | --- | --- |
| `path_hash` | `relative_path` | 判断路径是否变化 |
| `content_hash` | Markdown 正文 | 判断正文是否变化 |
| `front_matter_hash` | Front Matter 关键字段 | 判断元数据是否变化 |

如果三个哈希均未变化：

```text
status=unchanged
```

同步服务不会修改数据库记录，也不会刷新 `last_scanned_at`、`last_synced_at` 或系统 `updated_at`。

如果任一哈希发生变化：

```text
status=updated
```

同步服务会更新同一条 `knowledge_documents` 记录。

## 4. 更新字段

发生变化时，以下字段会按最新解析结果更新：

| 字段 | 说明 |
| --- | --- |
| `title` | 文档标题 |
| `category` | 文档分类 |
| `summary` | 文档摘要 |
| `body` | Markdown 正文 |
| `status` | 文档状态 |
| `visibility` | 可见性 |
| `language` | 文档语言 |
| `relative_path` | 相对路径 |
| `absolute_path` | 绝对路径 |
| `path_hash` | 路径哈希 |
| `content_hash` | 正文哈希 |
| `front_matter_hash` | 元数据哈希 |
| `tags` | 标签 |
| `aliases` | 别名 |
| `source` | 来源信息 |
| `source_created_at` | Front Matter `created_at` |
| `source_updated_at` | Front Matter `updated_at` |
| `sync_status` | 更新成功后为 `synced` |
| `sync_error` | 更新成功后清空 |
| `last_scanned_at` | 本次扫描时间 |
| `last_synced_at` | 本次成功同步时间 |
| `is_deleted` | 更新成功后恢复为 `false` |
| `deleted_at` | 更新成功后清空 |

## 5. 时间字段语义

| 字段 | 含义 | 何时变化 |
| --- | --- | --- |
| `source_created_at` | Markdown Front Matter 中的创建时间 | Front Matter 变化时随解析结果更新 |
| `source_updated_at` | Markdown Front Matter 中的更新时间 | Front Matter 变化时随解析结果更新 |
| `last_scanned_at` | 系统执行有效同步的扫描时间 | 新增或更新成功时变化 |
| `last_synced_at` | 系统成功写入结构化存储的时间 | 新增或更新成功时变化 |
| `updated_at` | 数据库记录更新时间 | 数据库记录实际更新时变化 |

未变化文档返回 `unchanged`，不刷新上述系统同步时间，避免重复同步造成无意义写入。

## 6. 错误处理

如果 Markdown 解析失败：

- 返回 `error`。
- 不修改原有数据库记录。
- 返回解析错误列表。

## 7. 后续衔接

TB-V10-008 只负责内容或元数据变化更新。

后续 TB-V10-009 会在此基础上进一步完善文档移动识别，避免将复杂移动场景误判为新增或路径冲突。
