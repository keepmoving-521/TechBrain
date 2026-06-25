# TechBrain 新增文档同步说明

本文说明 TechBrain 如何将首次扫描到的 Markdown 文档写入结构化存储。

本能力对应 TB-V10-007，依赖：

- TB-V10-005：Markdown 内容解析。
- TB-V10-006：文档结构化数据模型。

## 1. 职责边界

新增文档同步负责：

- 读取扫描阶段发现的 Markdown 文件。
- 解析 Front Matter 和 Markdown 正文。
- 将合法文档写入 `knowledge_documents`。
- 保证重复执行不会产生重复记录。

本阶段不负责：

- 更新已存在文档。
- 处理文件移动后的路径修正。
- 处理软删除。
- 写入搜索索引。
- 生成向量。

这些能力会在后续同步需求中继续实现。

## 2. 同步入口

后端提供同步函数：

```python
from techbrain.knowledge.sync import sync_new_markdown_document

result = sync_new_markdown_document(session, markdown_file, encoding="utf-8")
```

输入：

| 参数 | 说明 |
| --- | --- |
| `session` | SQLAlchemy Session |
| `markdown_file` | TB-V10-004 扫描得到的 Markdown 文件 |
| `encoding` | Markdown 文件编码 |
| `scanned_at` | 可选，扫描时间 |

输出：

| 状态 | 说明 |
| --- | --- |
| `created` | 新文档已写入结构化存储 |
| `skipped` | 已存在同 ID 或同路径文档，未重复插入 |
| `error` | Markdown 解析失败，未写入数据库 |

## 3. 写入规则

合法 Markdown 文档会写入 `knowledge_documents`：

| 来源 | 目标字段 |
| --- | --- |
| Front Matter `id` | `document_id` |
| Front Matter `title` | `title` |
| Front Matter `category` | `category` |
| Front Matter `summary` | `summary` |
| Front Matter `tags` | `tags` |
| Front Matter `aliases` | `aliases` |
| Front Matter `source` | `source` |
| Front Matter `status` | `status` |
| Front Matter `visibility` | `visibility` |
| Front Matter `language` | `language` |
| Front Matter `created_at` | `source_created_at` |
| Front Matter `updated_at` | `source_updated_at` |
| Markdown 正文 | `body` |
| Markdown 相对路径 | `relative_path` |
| Markdown 绝对路径 | `absolute_path` |

同步服务还会生成：

| 字段 | 说明 |
| --- | --- |
| `path_hash` | 相对路径 SHA-256 |
| `content_hash` | Markdown 正文 SHA-256 |
| `front_matter_hash` | Front Matter 关键字段指纹 SHA-256 |
| `sync_status` | 新增成功后为 `synced` |
| `sync_error` | 新增成功后为 `null` |
| `last_scanned_at` | 本次扫描时间 |
| `last_synced_at` | 本次同步时间 |
| `is_deleted` | 新增成功后为 `false` |

## 4. 幂等规则

新增同步必须是幂等的。

如果数据库中已存在以下任一记录，当前 Markdown 文件不会再次插入：

1. `document_id` 相同。
2. `relative_path` 相同。

返回结果为：

```text
skipped
```

这样可以保证重复扫描、重复执行同步任务时，不会产生重复数据。

## 5. 错误处理

如果 Markdown 解析失败：

1. 不写入 `knowledge_documents`。
2. 返回 `error`。
3. 返回解析阶段产生的错误列表。

示例错误：

```json
{
  "file_path": "backend/python/broken.md",
  "code": "FRONT_MATTER_MISSING",
  "message": "Front Matter 必须位于文件顶部并以 --- 开始",
  "line": 1,
  "column": 1
}
```

## 6. 后续衔接

TB-V10-007 只处理新增文档。

后续需求会继续实现：

- 已有文档内容更新。
- 文档移动识别。
- 源文件删除后的软删除。
- 同步批处理和同步报告。
