# TechBrain 同步任务记录说明

本文说明 TechBrain 如何记录每次 Markdown 知识库同步任务的执行结果和失败详情。

本能力对应 TB-V10-012，依赖 TB-V10-011。

## 1. 设计目标

同步任务记录用于回答这些问题：

- 最近一次同步是否成功？
- 本次同步处理了多少文档？
- 新增、修改、恢复、未变化、删除分别有多少？
- 哪些文件失败？
- 失败发生在扫描、解析还是同步阶段？
- 失败字段、行号和列号在哪里？

## 2. 数据表

新增两张表：

```text
knowledge_sync_tasks
knowledge_sync_failures
```

### 2.1 `knowledge_sync_tasks`

记录一次全量同步任务摘要。

| 字段 | 说明 |
| --- | --- |
| `id` | 任务 ID |
| `status` | 任务状态 |
| `started_at` | 任务开始时间 |
| `finished_at` | 任务结束时间 |
| `scanned_count` | 扫描到的 Markdown 文件数 |
| `success_count` | 成功处理数 |
| `failed_count` | 失败数 |
| `created_count` | 新增数 |
| `updated_count` | 更新数 |
| `restored_count` | 恢复数 |
| `unchanged_count` | 未变化数 |
| `deleted_count` | 软删除数 |
| `created_at` | 记录创建时间 |

任务状态：

| 状态 | 说明 |
| --- | --- |
| `success` | 没有失败项 |
| `partial_success` | 部分成功、部分失败 |
| `failed` | 没有成功处理项且存在失败 |

### 2.2 `knowledge_sync_failures`

记录一次同步任务中的失败明细。

| 字段 | 说明 |
| --- | --- |
| `id` | 失败记录 ID |
| `task_id` | 所属任务 ID |
| `path` | 失败文件路径 |
| `stage` | 失败阶段 |
| `code` | 错误码 |
| `message` | 错误信息 |
| `field` | 可选，失败字段 |
| `line` | 可选，行号 |
| `column` | 可选，列号 |
| `created_at` | 记录创建时间 |

失败阶段：

| 阶段 | 说明 |
| --- | --- |
| `scan` | 文件扫描阶段 |
| `parse` | Markdown / Front Matter 解析阶段 |
| `sync` | 结构化入库同步阶段 |

## 3. 同步任务落库

全量同步默认会记录任务结果：

```python
from techbrain.knowledge.task import run_full_knowledge_sync

result = run_full_knowledge_sync(session, config)
```

返回结果中包含：

```python
result.task_id
```

如需仅执行同步、不记录任务历史，可显式关闭：

```python
result = run_full_knowledge_sync(session, config, record_task=False)
```

## 4. 查询任务结果

查询任务列表：

```python
from techbrain.knowledge.task import list_sync_tasks_statement

tasks = session.scalars(list_sync_tasks_statement()).all()
```

查询单个任务：

```python
from techbrain.knowledge.task import get_sync_task_statement

task = session.scalar(get_sync_task_statement(task_id))
```

任务对象可通过 `failures` 查看失败明细。

## 5. 失败定位示例

Front Matter 缺失时，失败记录示例：

```json
{
  "path": "backend/python/broken.md",
  "stage": "parse",
  "code": "FRONT_MATTER_MISSING",
  "message": "Front Matter 必须位于文件顶部并以 --- 开始",
  "line": 1,
  "column": 1
}
```

扫描失败时，失败阶段为：

```text
scan
```

路径冲突等结构化同步失败时，失败阶段为：

```text
sync
```

## 6. 迁移

最新迁移版本：

```text
0004
```

执行：

```powershell
cd backend
python -m techbrain.db.migrate upgrade head
```

空数据库升级后应包含：

```text
knowledge_sync_tasks
knowledge_sync_failures
```

## 7. 后续衔接

TB-V10-012 只负责同步任务结果持久化和查询基础。

后续需求会继续实现：

- 手动触发同步 API。
- 同步任务状态页面。
- 并发控制和任务锁。
- 失败重试和告警。
