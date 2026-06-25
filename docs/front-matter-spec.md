# TechBrain Front Matter 元数据规范

## 1. 文档目的

本文定义 TechBrain Markdown 文档的 Front Matter 元数据规范。

该规范用于：

- 为每篇 Markdown 文档提供稳定身份和基础属性。
- 支撑 Markdown 扫描、解析、同步、分类、标签、搜索和 RAG 切片。
- 保证平台内编辑元数据时可以安全回写 Markdown。
- 为后续兼容升级提供版本化基础。

本文依赖：[Markdown 知识目录规范](markdown-knowledge-spec.md)。

## 2. Front Matter 格式

Front Matter 必须位于 Markdown 文件顶部，使用 YAML 格式，并由 `---` 包裹。

正确示例：

```markdown
---
schema_version: 1
id: sqlalchemy-joinedload
title: SQLAlchemy joinedload 使用指南
category: backend/python
tags:
  - orm
  - sqlalchemy
  - performance
status: published
created_at: 2026-06-25T10:00:00+08:00
updated_at: 2026-06-25T10:30:00+08:00
summary: SQLAlchemy joinedload 的适用场景、常见误区和实践示例。
source:
  type: original
---

# SQLAlchemy joinedload 使用指南
```

错误示例：

```markdown
# SQLAlchemy joinedload 使用指南

---
id: sqlalchemy-joinedload
title: SQLAlchemy joinedload 使用指南
---
```

错误原因：

- Front Matter 不在文件顶部。

## 3. 字段总览

| 字段 | 必填 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `schema_version` | 是 | integer | 无 | Front Matter 规范版本 |
| `id` | 是 | string | 无 | 稳定文档 ID |
| `title` | 是 | string | 无 | 文档标题 |
| `category` | 是 | string | 无 | 主分类路径 |
| `tags` | 否 | string array | `[]` | 标签列表 |
| `status` | 否 | string enum | `published` | 文档状态 |
| `created_at` | 是 | datetime | 无 | 文档创建时间 |
| `updated_at` | 是 | datetime | 无 | 文档最后更新时间 |
| `summary` | 否 | string | `null` | 文档摘要 |
| `source` | 否 | object | `{ type: "original" }` | 来源信息 |
| `aliases` | 否 | string array | `[]` | 别名、曾用名或搜索同义词 |
| `language` | 否 | string | `zh-CN` | 文档主要语言 |
| `visibility` | 否 | string enum | `private` | 可见性 |

## 4. 必填字段

### 4.1 `schema_version`

Front Matter 规范版本。

类型：

```text
integer
```

当前版本：

```yaml
schema_version: 1
```

校验规则：

- 必填。
- 必须为正整数。
- 当前只接受 `1`。
- 后续规范升级时通过该字段做兼容解析。

错误示例：

```yaml
schema_version: "1"
```

错误原因：

- 类型错误，应为 integer。

### 4.2 `id`

文档稳定 ID，用于识别同一篇文档。

类型：

```text
string
```

正确示例：

```yaml
id: sqlalchemy-joinedload
```

校验规则：

- 必填。
- 在整个知识库内必须唯一。
- 创建后不应修改。
- 文件移动或重命名时，`id` 保持不变。
- 长度建议 `3` 到 `120` 个字符。
- 推荐使用小写英文、数字和连字符。
- 正则建议：

```regex
^[a-z0-9][a-z0-9-]{1,118}[a-z0-9]$
```

允许：

```yaml
id: mysql-index-optimization
id: rag-chunking-strategy
id: fastapi-dependency-injection
```

不推荐或非法：

```yaml
id: SQLAlchemy JoinedLoad
id: sqlalchemy_joinedload
id: /backend/python/joinedload
id: 2026-06-25
```

说明：

- 不使用路径作为 ID，避免移动文件导致身份变化。
- 不使用纯日期作为 ID，主题不可读且容易冲突。

### 4.3 `title`

文档标题。

类型：

```text
string
```

正确示例：

```yaml
title: SQLAlchemy joinedload 使用指南
```

校验规则：

- 必填。
- 去除首尾空白后不能为空。
- 长度建议 `1` 到 `120` 个字符。
- 应与正文一级标题保持一致或语义一致。
- 不应包含换行。
- 不应包含 Markdown 标题前缀 `#`。

错误示例：

```yaml
title: "# SQLAlchemy joinedload 使用指南"
```

错误原因：

- `title` 是纯文本，不应包含 Markdown 标记。

### 4.4 `category`

文档主分类路径。

类型：

```text
string
```

正确示例：

```yaml
category: backend/python
```

校验规则：

- 必填。
- 使用 `/` 表达层级。
- 必须与 Markdown 知识目录中的分类目录一致。
- 不以 `/` 开头或结尾。
- 不允许出现 `..`。
- 不允许指向保留目录：`assets`、`drafts`、`archive`。
- 推荐使用小写英文、数字和连字符。

正确：

```yaml
category: database/mysql
category: infrastructure/docker
category: ai/rag
```

错误：

```yaml
category: /backend/python
category: backend/python/
category: ../private
category: assets/images
category: Python/SQLAlchemy
```

说明：

- V1.0 中一篇文档只有一个主分类。
- 跨主题能力通过 `tags` 表达，不通过多个分类表达。

### 4.5 `created_at`

文档创建时间。

类型：

```text
datetime
```

正确示例：

```yaml
created_at: 2026-06-25T10:00:00+08:00
```

校验规则：

- 必填。
- 使用 ISO 8601 / RFC 3339 格式。
- 必须包含时区偏移。
- 创建后不应随同步自动变化。

错误示例：

```yaml
created_at: 2026-06-25
created_at: "2026/06/25 10:00"
created_at: yesterday
```

错误原因：

- 日期缺少时间和时区。
- 非标准格式。
- 模糊时间不可解析。

### 4.6 `updated_at`

文档最后更新时间。

类型：

```text
datetime
```

正确示例：

```yaml
updated_at: 2026-06-25T10:30:00+08:00
```

校验规则：

- 必填。
- 使用 ISO 8601 / RFC 3339 格式。
- 必须包含时区偏移。
- 不得早于 `created_at`。
- 当正文或元数据发生有意义修改时应更新。

错误示例：

```yaml
created_at: 2026-06-25T10:00:00+08:00
updated_at: 2026-06-24T10:00:00+08:00
```

错误原因：

- `updated_at` 早于 `created_at`。

## 5. 可选字段

### 5.1 `tags`

文档标签列表，用于表达跨分类主题。

类型：

```text
string array
```

默认值：

```yaml
tags: []
```

正确示例：

```yaml
tags:
  - orm
  - sqlalchemy
  - performance
```

校验规则：

- 可选。
- 未提供时按空数组处理。
- 每个标签去除首尾空白后不能为空。
- 同一文档内标签不得重复。
- 标签建议使用小写英文、数字、中文或连字符。
- 单个标签长度建议 `1` 到 `50` 个字符。
- 标签数量建议不超过 `20` 个。

错误示例：

```yaml
tags:
  - ORM
  - orm
  - ""
```

错误原因：

- 大小写混用容易造成重复标签。
- 空标签无意义。

### 5.2 `status`

文档状态。

类型：

```text
string enum
```

默认值：

```yaml
status: published
```

允许值：

| 值 | 说明 | 默认展示 | 默认索引 | 默认进入 RAG |
| --- | --- | --- | --- | --- |
| `published` | 正式文档 | 是 | 是 | 是 |
| `draft` | 草稿 | 否 | 否 | 否 |
| `archived` | 归档 | 否 | 可配置 | 可配置 |
| `deprecated` | 已过时但仍可参考 | 是 | 是 | 可配置 |

校验规则：

- 可选。
- 未提供时视为 `published`。
- 如果文件位于 `drafts/`，状态应为 `draft` 或缺省后由扫描器按目录推断为 `draft`。
- 如果文件位于 `archive/`，状态应为 `archived` 或缺省后由扫描器按目录推断为 `archived`。
- 状态值必须小写。

错误示例：

```yaml
status: Published
status: done
```

错误原因：

- 枚举值大小写错误。
- 使用了未定义状态。

### 5.3 `summary`

文档摘要。

类型：

```text
string | null
```

默认值：

```yaml
summary: null
```

校验规则：

- 可选。
- 建议 `20` 到 `300` 个字符。
- 不应包含 Markdown 图片、HTML、脚本。
- 不应简单重复标题。

正确示例：

```yaml
summary: 介绍 SQLAlchemy joinedload 的适用场景、查询行为和常见误区。
```

### 5.4 `source`

来源信息，用于追踪文档来源。

类型：

```text
object
```

默认值：

```yaml
source:
  type: original
```

字段：

| 字段 | 必填 | 类型 | 说明 |
| --- | --- | --- | --- |
| `source.type` | 是 | enum | 来源类型 |
| `source.url` | 否 | string | 外部来源 URL |
| `source.title` | 否 | string | 外部来源标题 |
| `source.author` | 否 | string | 作者或来源方 |
| `source.retrieved_at` | 否 | datetime | 获取时间 |
| `source.note` | 否 | string | 来源说明 |

`source.type` 允许值：

| 值 | 说明 |
| --- | --- |
| `original` | 原创 |
| `excerpt` | 摘录 |
| `translation` | 翻译 |
| `summary` | 总结 |
| `ai_generated` | AI 生成 |
| `imported` | 从外部系统导入 |

原创示例：

```yaml
source:
  type: original
```

外部资料总结示例：

```yaml
source:
  type: summary
  url: https://docs.sqlalchemy.org/
  title: SQLAlchemy Documentation
  retrieved_at: 2026-06-25T10:00:00+08:00
```

AI 草稿示例：

```yaml
source:
  type: ai_generated
  note: 由 AI 根据个人笔记生成，尚未人工审核。
```

校验规则：

- `source.type` 必须存在。
- `source.url` 如存在，必须为 `http` 或 `https` URL。
- `source.retrieved_at` 如存在，必须包含时区。
- `source.type` 为 `ai_generated` 时，文档状态建议为 `draft`。

### 5.5 `aliases`

别名、曾用名或搜索同义词。

类型：

```text
string array
```

默认值：

```yaml
aliases: []
```

示例：

```yaml
aliases:
  - eager loading
  - 预加载
```

校验规则：

- 可选。
- 去重后保存。
- 单个别名长度建议不超过 `80` 个字符。
- 不应放入大量关键词；大量主题应使用正文或标签表达。

### 5.6 `language`

文档主要语言。

类型：

```text
string
```

默认值：

```yaml
language: zh-CN
```

建议值：

```text
zh-CN
en
ja
```

校验规则：

- 使用 BCP 47 语言标签。
- 未提供时按 `zh-CN` 处理。

### 5.7 `visibility`

可见性。

类型：

```text
string enum
```

默认值：

```yaml
visibility: private
```

允许值：

| 值 | 说明 |
| --- | --- |
| `private` | 仅个人可见 |
| `shared` | 可在受控范围内分享 |

当前 TechBrain 是个人知识库，默认均为 `private`。

## 6. 完整正确示例

```markdown
---
schema_version: 1
id: sqlalchemy-joinedload
title: SQLAlchemy joinedload 使用指南
category: backend/python
tags:
  - orm
  - sqlalchemy
  - performance
status: published
created_at: 2026-06-25T10:00:00+08:00
updated_at: 2026-06-25T10:30:00+08:00
summary: 介绍 SQLAlchemy joinedload 的适用场景、查询行为和常见误区。
source:
  type: original
aliases:
  - eager loading
  - 预加载
language: zh-CN
visibility: private
---

# SQLAlchemy joinedload 使用指南

正文内容……
```

## 7. 最小正确示例

```markdown
---
schema_version: 1
id: mysql-index-optimization
title: MySQL 索引优化笔记
category: database/mysql
created_at: 2026-06-25T10:00:00+08:00
updated_at: 2026-06-25T10:00:00+08:00
---

# MySQL 索引优化笔记

正文内容……
```

等价默认值：

```yaml
tags: []
status: published
summary: null
source:
  type: original
aliases: []
language: zh-CN
visibility: private
```

## 8. 错误示例

```markdown
---
id: SQLAlchemy JoinedLoad
title: "# joinedload"
category: /backend/python/
tags:
  - ORM
  - orm
  - ""
status: done
created_at: 2026-06-25
updated_at: 2026-06-24T10:00:00+08:00
source:
  type: ai
  url: file:///C:/Users/me/private.md
---

# joinedload
```

错误原因：

- 缺少 `schema_version`。
- `id` 包含空格和大写，不符合稳定 ID 规则。
- `title` 包含 Markdown 标题符号。
- `category` 以 `/` 开头和结尾。
- `tags` 存在大小写重复和空标签。
- `status` 使用了未定义枚举值。
- `created_at` 缺少时间和时区。
- `updated_at` 早于 `created_at`。
- `source.type` 使用了未定义枚举值。
- `source.url` 使用本地文件路径，不允许。

## 9. 状态与目录兼容规则

目录和 Front Matter 状态应保持一致。

| 文件位置 | 缺省状态推断 | 推荐显式状态 |
| --- | --- | --- |
| 分类目录 | `published` | `published` 或 `deprecated` |
| `drafts/` | `draft` | `draft` |
| `archive/` | `archived` | `archived` |

冲突处理建议：

| 场景 | 处理方式 |
| --- | --- |
| 文件在 `drafts/`，但 `status: published` | 校验警告；默认按 `draft` 处理 |
| 文件在 `archive/`，但 `status: published` | 校验警告；默认按 `archived` 处理 |
| 文件在正式分类目录，但 `status: draft` | 校验警告；建议移动到 `drafts/` |
| 文件在正式分类目录，但 `status: archived` | 校验警告；建议移动到 `archive/` |

## 10. 分类字段与目录兼容规则

`category` 应与文件所在分类目录一致。

示例：

```text
backend/python/sqlalchemy-joinedload.md
```

应使用：

```yaml
category: backend/python
```

如果不一致：

```yaml
category: database/mysql
```

处理方式：

- 首次扫描应记录校验错误或警告。
- 默认不静默修正 Markdown。
- 后续平台编辑可以提供“按目录修正 category”或“移动文件到 category 对应目录”的显式操作。

## 11. 兼容策略

### 11.1 规范版本

当前版本：

```yaml
schema_version: 1
```

兼容规则：

- 缺少 `schema_version` 的文档视为旧文档，不直接拒绝读取，但应产生校验警告。
- 旧文档可以进入“待补全元数据”状态。
- 后续版本新增字段必须提供默认值。
- 后续版本删除或改变字段含义时，必须提供迁移说明。

### 11.2 缺失可选字段

缺失可选字段时使用默认值，不修改源文件。

示例：

```yaml
tags: []
status: published
source:
  type: original
```

### 11.3 缺失必填字段

缺失必填字段时：

- 文档仍可作为原始 Markdown 文件保留。
- 同步服务应记录校验错误。
- 不应写入正式文档表的有效记录。
- 页面可在“待修复文档”视图中展示。

### 11.4 自动补全边界

系统可以建议补全：

- `title`
- `category`
- `tags`
- `summary`

系统不应静默生成或修改：

- `id`
- `created_at`
- `updated_at`
- `source`

除非用户明确确认写回。

## 12. 字段校验汇总

| 字段 | 校验规则 |
| --- | --- |
| `schema_version` | 必填，integer，只接受 `1` |
| `id` | 必填，全库唯一，推荐 kebab-case，创建后不变 |
| `title` | 必填，非空，纯文本，建议不超过 120 字符 |
| `category` | 必填，使用 `/` 分隔，不穿越路径，不使用保留目录 |
| `tags` | 可选，数组，去重，非空字符串，建议不超过 20 个 |
| `status` | 可选，枚举：`published`、`draft`、`archived`、`deprecated` |
| `created_at` | 必填，ISO 8601，必须带时区 |
| `updated_at` | 必填，ISO 8601，必须带时区，不早于 `created_at` |
| `summary` | 可选，纯文本，建议不超过 300 字符 |
| `source.type` | 可选但如有 `source` 则必填，枚举值 |
| `source.url` | 可选，必须为 http/https URL |
| `aliases` | 可选，数组，去重 |
| `language` | 可选，BCP 47，默认 `zh-CN` |
| `visibility` | 可选，枚举：`private`、`shared` |

## 13. 后续实现建议

解析器应输出三类结果：

1. `valid`：字段完整且校验通过。
2. `warning`：可兼容读取，但存在目录状态冲突、旧版本缺省等问题。
3. `error`：缺少必填字段、类型错误、时间非法、ID 冲突等问题。

错误信息建议包含：

```json
{
  "file_path": "backend/python/sqlalchemy-joinedload.md",
  "field": "updated_at",
  "code": "FRONT_MATTER_INVALID_TIME_ORDER",
  "message": "updated_at 不得早于 created_at"
}
```

## 14. 开发检查清单

新增或修改 Markdown 文档时必须确认：

- [ ] Front Matter 位于文件顶部。
- [ ] `schema_version` 为 `1`。
- [ ] `id` 全库唯一且稳定。
- [ ] `title` 清晰且不包含 Markdown 标记。
- [ ] `category` 与目录一致。
- [ ] `tags` 无空值和重复值。
- [ ] `status` 使用允许枚举值。
- [ ] `created_at` 和 `updated_at` 带时区。
- [ ] `updated_at` 不早于 `created_at`。
- [ ] 外部来源 URL 使用 http/https。
- [ ] AI 生成内容明确标记来源，并优先保持草稿状态。
