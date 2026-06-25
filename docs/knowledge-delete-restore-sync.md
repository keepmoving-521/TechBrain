# TechBrain 文档删除与恢复同步说明

本文说明 TechBrain 如何在源 Markdown 文件删除后软删除文档，并在文件恢复后重新激活原文档记录。

本能力对应 TB-V10-010，依赖 TB-V10-007。

## 1. 核心原则

Markdown 是知识源，数据库保存同步后的结构化状态。

当某篇文档在一次扫描中不再出现时，不应立即物理删除数据库记录，而应软删除：

```text
is_deleted=true
sync_status=deleted
deleted_at=删除检测时间
```

这样可以保留原文档身份、关联数据和历史状态，便于后续恢复。

## 2. 软删除入口

后端提供函数：

```python
from techbrain.knowledge.sync import mark_missing_documents_deleted

result = mark_missing_documents_deleted(session, scanned_files)
```

输入：

| 参数 | 说明 |
| --- | --- |
| `session` | SQLAlchemy Session |
| `scanned_files` | 本轮扫描到的 Markdown 文件列表 |
| `deleted_at` | 可选，删除检测时间 |

处理规则：

1. 读取当前未删除文档。
2. 对比本轮扫描到的 `relative_path`。
3. 未在本轮扫描中出现的文档标记为软删除。
4. 已软删除文档不会重复处理。

## 3. 软删除字段变化

软删除时更新：

| 字段 | 值 |
| --- | --- |
| `is_deleted` | `true` |
| `deleted_at` | 删除检测时间 |
| `sync_status` | `deleted` |
| `sync_error` | `null` |
| `last_scanned_at` | 删除检测时间 |

软删除时不清空正文、Front Matter、路径、哈希或关联字段。

## 4. 正常列表与搜索过滤

已删除文档不应出现在正常列表和搜索中。

后端提供基础查询：

```python
from techbrain.knowledge.sync import active_knowledge_documents_statement

statement = active_knowledge_documents_statement()
```

该查询包含：

```text
is_deleted=false
```

后续知识列表、搜索索引、RAG 入库和推荐任务都应基于该过滤条件排除软删除文档。

## 5. 恢复规则

如果源 Markdown 文件恢复，并且 Front Matter `id` 与软删除记录的 `document_id` 一致：

1. 重新使用同一条数据库记录。
2. 保留数据库主键 `id`。
3. 保留可继续复用的关联数据。
4. 更新正文、元数据、路径和哈希。
5. 清除软删除状态。

恢复后字段：

| 字段 | 值 |
| --- | --- |
| `is_deleted` | `false` |
| `deleted_at` | `null` |
| `sync_status` | `synced` |
| `sync_error` | `null` |
| `last_scanned_at` | 恢复扫描时间 |
| `last_synced_at` | 恢复同步时间 |

同步结果返回：

```text
restored
```

## 6. 幂等性

删除同步是幂等的：

- 第一次检测缺失文档时返回删除数量。
- 同一文档已软删除后，后续再次检测不会重复计数。

恢复同步也是幂等的：

- 文件恢复后第一次同步返回 `restored`。
- 恢复后内容未变化的再次同步返回 `unchanged`。

## 7. 后续衔接

TB-V10-010 只负责文档主表的软删除与恢复。

后续全量同步任务会把扫描、解析、新增、修改、移动、删除和恢复统一编排起来。
