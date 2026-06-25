# TechBrain 文档结构化数据模型说明

本文说明 TechBrain Markdown 知识文档在数据库中的结构化存储模型。

本能力对应 TB-V10-006，依赖：

- TB-V01-004：数据库迁移机制。
- TB-V10-002：Front Matter 元数据规范。

## 1. 设计目标

文档结构化数据模型用于承接 Markdown 解析结果，为后续同步、检索、索引和知识图谱提供稳定数据基础。

模型必须支持：

- 新增文档。
- 修改文档内容或元数据。
- 移动文件路径。
- 软删除文档。
- 记录同步状态和失败原因。

## 2. 表设计

当前新增主表：

```text
knowledge_documents
```

一个表记录一篇 Markdown 知识文档的最新结构化状态。

## 3. 身份与路径字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | integer | 数据库自增主键 |
| `document_id` | string(120) | Front Matter 中的稳定文档 ID |
| `relative_path` | string(1024) | 相对知识库根目录的路径 |
| `absolute_path` | string(2048) | 当前扫描时解析出的绝对路径 |
| `path_hash` | string(64) | 路径哈希，用于快速判断路径变化 |

约束：

- `document_id` 唯一。
- `relative_path` 唯一。

移动文件时：

- `document_id` 保持不变。
- `relative_path`、`absolute_path`、`path_hash` 更新。

## 4. 内容与哈希字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `title` | string(200) | 文档标题 |
| `category` | string(255) | 主分类 |
| `summary` | text | 摘要 |
| `body` | text | Markdown 正文，不包含 Front Matter |
| `content_hash` | string(64) | Markdown 正文或完整内容哈希 |
| `front_matter_hash` | string(64) | Front Matter 哈希 |

修改文档时：

- 正文变化更新 `content_hash`。
- 元数据变化更新 `front_matter_hash`。
- 标题、分类、摘要等结构化字段按解析结果更新。

## 5. Front Matter 映射字段

| 字段 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `status` | string(32) | `published` | 文档生命周期状态 |
| `visibility` | string(32) | `private` | 可见性 |
| `language` | string(32) | `zh-CN` | 文档语言 |
| `tags` | JSON | `[]` | 标签列表 |
| `aliases` | JSON | `[]` | 别名列表 |
| `source` | JSON | `{}` | 来源信息 |
| `source_created_at` | datetime | 无 | Front Matter `created_at` |
| `source_updated_at` | datetime | 无 | Front Matter `updated_at` |

`status` 支持：

- `published`
- `draft`
- `archived`
- `deprecated`

`visibility` 支持：

- `private`
- `shared`

## 6. 同步状态字段

| 字段 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `sync_status` | string(32) | `pending` | 当前同步状态 |
| `sync_error` | text | `null` | 最近一次同步失败原因 |
| `last_scanned_at` | datetime | `null` | 最近扫描时间 |
| `last_synced_at` | datetime | `null` | 最近成功同步时间 |

`sync_status` 支持：

- `pending`：待同步。
- `synced`：已同步。
- `failed`：同步失败。
- `deleted`：已标记删除。

## 7. 软删除字段

| 字段 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `is_deleted` | boolean | `false` | 是否软删除 |
| `deleted_at` | datetime | `null` | 软删除时间 |

当扫描发现源文件已不存在时，后续同步流程应：

1. 设置 `is_deleted=true`。
2. 设置 `deleted_at`。
3. 设置 `sync_status=deleted`。

不直接物理删除记录，以便保留历史状态、支持恢复和排查。

## 8. 系统时间字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `created_at` | datetime | 数据库记录创建时间 |
| `updated_at` | datetime | 数据库记录更新时间 |

这些字段表示系统记录时间，不等同于 Markdown Front Matter 中的 `created_at` 和 `updated_at`。

## 9. 索引

当前索引：

| 索引 | 说明 |
| --- | --- |
| `ix_knowledge_documents_document_id` | 按稳定文档 ID 查询 |
| `ix_knowledge_documents_relative_path` | 按相对路径查询 |
| `ix_knowledge_documents_path_hash` | 判断路径变化 |
| `ix_knowledge_documents_content_hash` | 判断内容变化 |
| `ix_knowledge_documents_status` | 按文档状态过滤 |
| `ix_knowledge_documents_sync_status` | 按同步状态过滤 |
| `ix_knowledge_documents_is_deleted` | 过滤软删除记录 |

## 10. 典型状态变化

### 10.1 新增

```text
不存在 document_id
    ↓
插入 knowledge_documents
    ↓
sync_status=pending
```

### 10.2 修改

```text
document_id 已存在
content_hash 或 front_matter_hash 变化
    ↓
更新结构化字段
    ↓
sync_status=pending
```

### 10.3 移动

```text
document_id 已存在
relative_path 变化
    ↓
更新 relative_path / absolute_path / path_hash
    ↓
保留同一条文档记录
```

### 10.4 软删除

```text
数据库存在记录
本轮扫描未发现源文件
    ↓
is_deleted=true
deleted_at=当前时间
sync_status=deleted
```

### 10.5 同步失败

```text
同步任务失败
    ↓
sync_status=failed
sync_error=失败原因
last_scanned_at=扫描时间
```

## 11. 迁移

最新迁移版本：

```text
0003
```

执行：

```powershell
cd backend
python -m techbrain.db.migrate upgrade head
```

空数据库升级到最新版本后，应包含：

```text
knowledge_documents
```

## 12. 后续衔接

TB-V10-006 只建立文档主表和最新状态模型。

后续需求可以在此基础上继续增加：

- 文档标题层级表。
- 文档代码块表。
- 文档链接表。
- 文档同步历史表。
- 文档版本历史表。
