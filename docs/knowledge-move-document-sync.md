# TechBrain 文档移动识别说明

本文说明 TechBrain 如何识别 Markdown 文件路径变化，避免将移动误判为删除加新增。

本能力对应 TB-V10-009，依赖 TB-V10-008。

## 1. 核心原则

文档身份以 Front Matter 中的 `id` 为准。

```yaml
id: sqlalchemy-joinedload
```

只要 `id` 不变，即使 Markdown 文件从一个目录移动到另一个目录，也应视为同一篇文档。

## 2. 移动识别规则

同步服务按以下顺序判断文档身份：

1. 优先按 `document_id` 查找已存在记录。
2. 如果找到同 `document_id` 记录，则认为是同一篇文档。
3. 如果 `relative_path` 发生变化，则更新路径字段。
4. 不新增记录，不删除旧记录。

移动后更新字段：

| 字段 | 说明 |
| --- | --- |
| `relative_path` | 新相对路径 |
| `absolute_path` | 新绝对路径 |
| `path_hash` | 新路径哈希 |
| `last_scanned_at` | 本次扫描时间 |
| `last_synced_at` | 本次同步时间 |
| `sync_status` | 更新为 `synced` |
| `sync_error` | 清空 |

保留字段：

| 字段 | 说明 |
| --- | --- |
| `id` | 数据库主键不变 |
| `document_id` | Front Matter 稳定 ID 不变 |
| `content_hash` | 正文未变化时保持不变 |
| `front_matter_hash` | 元数据未变化时保持不变 |
| 关联数据 | 后续标题、链接、索引等关联数据可继续基于同一文档主键维护 |

## 3. 路径冲突

如果移动后的路径已经被另一篇文档占用，同步服务不会覆盖该记录。

此时返回错误：

```text
DOCUMENT_PATH_CONFLICT
```

该错误用于保护已有文档，避免错误地把两篇文档合并。

## 4. 与新增同步的区别

新增同步入口 `sync_new_markdown_document` 保持幂等插入语义：

- 已存在同 `document_id` 时跳过。
- 已存在同 `relative_path` 时跳过。

通用同步入口 `sync_markdown_document` 支持移动识别：

- 同 `document_id` 但路径不同：更新同一条记录。
- 不同 `document_id` 但路径相同：返回路径冲突错误。

## 5. 示例

初始文件：

```text
backend/python/sqlalchemy-joinedload.md
```

Front Matter：

```yaml
id: sqlalchemy-joinedload
```

移动后：

```text
backend/sqlalchemy/sqlalchemy-joinedload.md
```

同步结果：

```text
status=updated
document_id=sqlalchemy-joinedload
relative_path=backend/sqlalchemy/sqlalchemy-joinedload.md
```

数据库仍只有一条文档记录。

## 6. 后续衔接

TB-V10-009 只负责识别路径移动并更新文档主表。

后续需求可以在此基础上继续处理：

- 关联表的路径冗余字段刷新。
- 搜索索引中的文档路径更新。
- 同步历史记录。
- 移动事件审计。
