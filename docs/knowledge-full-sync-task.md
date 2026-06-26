# TechBrain 全量同步任务说明

本文说明 TechBrain 如何将扫描、解析、新增、修改、移动、删除和恢复组织为一次完整同步任务。

本能力对应 TB-V10-011，依赖 TB-V10-007 至 TB-V10-010。

## 1. 职责边界

全量同步任务负责把已有能力编排起来：

1. 扫描 Markdown 知识目录。
2. 逐个同步扫描到的 Markdown 文件。
3. 处理新增文档。
4. 处理修改文档。
5. 处理移动文档。
6. 处理恢复文档。
7. 标记本轮缺失的文档为软删除。
8. 汇总同步结果和失败明细。

本阶段不负责：

- 提供手动触发 API。
- 并发任务控制。
- 搜索索引刷新。
- 向量索引刷新。

这些能力会在后续需求中实现。

## 2. 同步入口

后端提供函数：

```python
from techbrain.knowledge.task import run_full_knowledge_sync

result = run_full_knowledge_sync(session, config)
```

输入：

| 参数 | 说明 |
| --- | --- |
| `session` | SQLAlchemy Session |
| `config` | 已校验的 `KnowledgeRepositoryConfig` |
| `started_at` | 可选，任务开始时间 |

## 3. 执行流程

```text
KnowledgeRepositoryConfig
    ↓
scan_markdown_files
    ↓
for each MarkdownFile
    ↓
sync_markdown_document
    ↓
mark_missing_documents_deleted
    ↓
KnowledgeFullSyncResult
```

单个文档解析失败或同步失败时，会记录失败明细，但不会阻塞其他文档继续处理。

## 4. 输出结果

`KnowledgeFullSyncResult` 包含：

| 字段 | 说明 |
| --- | --- |
| `started_at` | 任务开始时间 |
| `finished_at` | 任务结束时间 |
| `scanned_count` | 扫描到的 Markdown 文件数量 |
| `created_count` | 新增数量 |
| `updated_count` | 更新数量 |
| `restored_count` | 恢复数量 |
| `unchanged_count` | 未变化数量 |
| `deleted_count` | 软删除数量 |
| `failed_count` | 失败数量 |
| `failures` | 失败明细 |
| `success_count` | 成功处理的 Markdown 文件数量 |

失败明细包含：

| 字段 | 说明 |
| --- | --- |
| `path` | 文件路径 |
| `stage` | 失败阶段：`scan`、`parse` 或 `sync` |
| `code` | 错误码 |
| `message` | 错误说明 |
| `field` | 可选，字段名 |
| `line` | 可选，行号 |
| `column` | 可选，列号 |

## 5. 幂等性

全量同步任务应支持重复执行。

当知识库文件未变化时：

- 不新增重复文档。
- 不重复更新已有文档。
- 文档返回 `unchanged`。
- 不刷新未变化文档的同步时间。

## 6. 删除与恢复

全量同步以本轮扫描结果作为当前源文件集合：

- 数据库中存在但本轮未扫描到的活动文档会被软删除。
- 已软删除文档再次扫描到且 `document_id` 不变时会恢复。

## 7. 事务边界

当前实现由调用方传入 SQLAlchemy Session，全量同步函数在处理完成后提交事务。

同步任务记录表已在 TB-V10-012 中引入。后续可以进一步细化为：

- 任务记录事务。
- 单文档处理事务。
- 搜索索引刷新事务。

## 8. 后续衔接

TB-V10-011 只负责同步任务编排和结果汇总。

后续需求会继续实现：

- TB-V10-013：手动触发同步。
- 搜索索引刷新。
- 向量索引刷新。

同步任务记录已在 TB-V10-012 中实现，详见：[同步任务记录说明](knowledge-sync-task-record.md)。
