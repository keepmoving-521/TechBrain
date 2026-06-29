# 标签数据模型说明

本文档对应 TB-V10-020：建立标签数据模型。

## 1. 设计目标

标签用于表达跨分类主题和技术特征。一篇文档可以关联多个标签，一个标签也可以关联多篇文档。

本迭代建立：

- 结构化标签表 `knowledge_tags`。
- 文档标签多对多关联表 `knowledge_document_tags`。
- 标签名称规范化和数据库唯一约束。
- 标签与文档的 ORM 双向关系。

Markdown Front Matter 的 `tags` 和 `knowledge_documents.tags` JSON 镜像暂时保留。TB-V10-021 将负责根据 Markdown 自动创建标签并同步结构化关联。

## 2. 标签表

表名：`knowledge_tags`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `id` | integer | 是 | 标签主键 |
| `name` | string(80) | 是 | 标签展示名称 |
| `normalized_name` | string(80) | 是 | 标签规范化唯一键 |
| `status` | string(32) | 是 | 标签状态 |
| `created_at` | datetime | 是 | 创建时间 |
| `updated_at` | datetime | 是 | 更新时间 |

标签状态：

| 状态 | 说明 |
| --- | --- |
| `active` | 正常使用 |
| `archived` | 已归档，保留历史关系 |

## 3. 标签名称规范化

规范化用于识别技术含义相同但写法不同的标签。处理顺序：

1. 使用 Unicode NFKC 规范化字符。
2. 去除首尾空白。
3. 将连续空白合并为一个普通空格。
4. 使用 Unicode `casefold` 进行大小写无关归一化。

示例：

| 原名称 | 展示名称 | `normalized_name` |
| --- | --- | --- |
| ` ORM ` | `ORM` | `orm` |
| `orm` | `orm` | `orm` |
| 全角 `ＯＲＭ` | `ORM` | `orm` |
| `性能   优化` | `性能 优化` | `性能 优化` |

因此上述前三种 ORM 写法不能同时创建为不同标签。

当前规范化只处理字符形式、大小写和空白差异，不自动判断单复数、缩写或同义词。`cache` 与 `caching`、`ai` 与 `人工智能` 仍是不同标签，后续由标签合并能力显式处理。

## 4. 名称校验

标签展示名称：

- Unicode 规范化并去除多余空白后不能为空。
- 最大长度为 80 个字符。
- 不允许包含换行、制表符、零宽字符等控制或格式字符。
- 规范化唯一键最大长度同样为 80 个字符。
- 支持中文、英文、数字、空格和常见可见符号。

`normalized_name` 建立数据库唯一索引。唯一性覆盖所有状态，比“有效标签不可重复”更严格：归档标签也不会被同名重新创建，后续可选择恢复或合并原标签。

## 5. 文档标签关联表

表名：`knowledge_document_tags`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `document_id` | integer | 是 | 文档 ID，关联 `knowledge_documents.id` |
| `tag_id` | integer | 是 | 标签 ID，关联 `knowledge_tags.id` |
| `created_at` | datetime | 是 | 关联创建时间 |

`document_id + tag_id` 构成联合主键：

- 同一文档不能重复关联同一标签。
- 一篇文档可以通过不同 `tag_id` 关联多个标签。
- 一个标签可以关联多篇文档。

两个外键都使用 `ON DELETE CASCADE`：

- 文档物理删除时自动清理标签关联。
- 标签物理删除时自动清理文档关联。
- 删除关联不会删除另一侧实体。

## 6. ORM 关系

文档模型：

```text
KnowledgeDocument.tag_nodes -> list[KnowledgeTag]
```

标签模型：

```text
KnowledgeTag.documents -> list[KnowledgeDocument]
```

`KnowledgeDocument.tags` 仍是 Markdown Front Matter 标签字符串数组镜像；`tag_nodes` 是结构化标签关系。两者在 TB-V10-021 同步后应保持一致。

## 7. 索引与约束

核心约束：

- `knowledge_tags.normalized_name` 唯一。
- 标签状态只能是 `active` 或 `archived`。
- 文档标签关联联合主键防止重复关联。
- 文档和标签外键保证关联对象存在。

核心索引：

- `ix_knowledge_tags_normalized_name`：按规范化名称定位标签。
- `ix_knowledge_tags_status`：按状态过滤标签。
- `ix_knowledge_document_tags_tag_id`：反向查询标签关联文档。

## 8. 数据库迁移

迁移版本：`0007`

```powershell
cd backend
python -m techbrain.db.migrate upgrade
```

迁移只创建标签和关联表，不回填现有 `knowledge_documents.tags` JSON。这样可以保持本需求边界清晰，并由 TB-V10-021 使用统一同步规则完成首次结构化关联。

## 9. 验收结论

TB-V10-020 已覆盖：

- 标签名称具备稳定、明确的规范化规则。
- 数据库唯一约束阻止同一规范化名称重复存在。
- 标签支持正常与归档状态。
- 文档和标签形成多对多关系。
- 一篇文档可以关联多个结构化标签。
- 重复文档标签关联由联合主键阻止。
