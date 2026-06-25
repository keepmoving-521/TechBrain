# TechBrain Markdown 内容解析说明

本文说明 TechBrain 如何解析 Markdown 知识文档内容。

本能力对应 TB-V10-005，依赖：

- TB-V10-002：Front Matter 元数据规范。
- TB-V10-004：Markdown 文件扫描。

## 1. 职责边界

Markdown 内容解析负责把单个 Markdown 文件转换为统一解析结果。

解析内容包括：

- Front Matter。
- Markdown 正文。
- 标题层级。
- 围栏代码块。
- Markdown 内联链接。

本阶段不负责：

- 判断文档 ID 全库唯一。
- 写入 MySQL。
- 写入 ElasticSearch。
- 生成向量。
- 执行 AI 总结。

## 2. 输入

解析器消费 TB-V10-004 扫描得到的 `MarkdownFile`：

```python
from techbrain.knowledge.parser import parse_markdown_file

result = parse_markdown_file(markdown_file, encoding="utf-8")
```

也可以在测试或后续同步流程中直接解析字符串内容：

```python
from techbrain.knowledge.parser import parse_markdown_content

result = parse_markdown_content(markdown_file, content)
```

## 3. 输出

解析结果包含：

| 字段 | 说明 |
| --- | --- |
| `status` | `valid` 或 `error` |
| `document` | 合法文档的统一解析结构 |
| `errors` | 解析错误列表 |

合法文档结构包含：

| 字段 | 说明 |
| --- | --- |
| `file` | 扫描阶段发现的 Markdown 文件信息 |
| `front_matter` | 校验后的 Front Matter 元数据 |
| `body` | Markdown 正文 |
| `headings` | 标题层级列表 |
| `code_blocks` | 围栏代码块列表 |
| `links` | Markdown 内联链接列表 |
| `warnings` | 可兼容读取但需要提示的问题 |

## 4. Front Matter 解析

Front Matter 必须位于文件顶部，并使用 `---` 包裹：

```markdown
---
schema_version: 1
id: sqlalchemy-joinedload
title: SQLAlchemy joinedload 使用指南
category: backend/python
created_at: 2026-06-25T10:00:00+08:00
updated_at: 2026-06-25T10:30:00+08:00
---

# SQLAlchemy joinedload 使用指南
```

解析器当前支持 Front Matter 规范所需的 YAML 子集：

- `key: value` 标量。
- 空数组 `[]`。
- `null`。
- 缩进数组。
- 一层嵌套对象，例如 `source`。
- 单引号和双引号包裹的字符串。

如果 Front Matter 不在文件顶部、缺少结束标记或 YAML 子集格式错误，解析器会返回 `error`。

## 5. 字段校验

当前解析器校验以下规则：

| 字段 | 校验 |
| --- | --- |
| `schema_version` | 必填，integer，只接受 `1` |
| `id` | 必填，符合稳定 ID 格式 |
| `title` | 必填，非空，不以 Markdown 标题符号开头 |
| `category` | 必填，不以 `/` 开头或结尾，不包含 `..`，不指向保留目录 |
| `tags` | 可选，数组，非空字符串，大小写不重复 |
| `status` | 可选，枚举：`published`、`draft`、`archived`、`deprecated` |
| `created_at` | 必填，ISO 8601，必须带时区 |
| `updated_at` | 必填，ISO 8601，必须带时区，且不早于 `created_at` |
| `source.type` | 可选，默认 `original`，必须使用允许值 |
| `source.url` | 可选，必须为 `http` 或 `https` URL |
| `source.retrieved_at` | 可选，ISO 8601，必须带时区 |
| `aliases` | 可选，数组，非空字符串，大小写不重复 |
| `language` | 可选，默认 `zh-CN` |
| `visibility` | 可选，枚举：`private`、`shared` |

## 6. Markdown 基础结构

### 6.1 标题层级

解析器识别 ATX 标题：

```markdown
# 一级标题
## 二级标题
### 三级标题
```

代码块内的 `#` 不会被识别为标题。

### 6.2 代码块

解析器识别围栏代码块：

````markdown
```python
query = select(User)
```
````

输出包括：

- 语言。
- 起始行。
- 结束行。
- 代码内容。

### 6.3 链接

解析器识别 Markdown 内联链接：

```markdown
[SQLAlchemy 文档](https://docs.sqlalchemy.org/)
```

代码块内的链接不会被提取。

## 7. 错误信息

错误信息包含文件路径、错误码、消息，以及可选的行号、列号和字段名。

示例：

```json
{
  "file_path": "backend/python/sqlalchemy-joinedload.md",
  "field": "updated_at",
  "code": "FRONT_MATTER_INVALID_TIME_ORDER",
  "message": "updated_at 不得早于 created_at"
}
```

常见错误码：

| 错误码 | 说明 |
| --- | --- |
| `FRONT_MATTER_MISSING` | Front Matter 不在文件顶部 |
| `FRONT_MATTER_NOT_CLOSED` | Front Matter 缺少结束 `---` |
| `YAML_INVALID_LINE` | YAML 行格式错误 |
| `YAML_UNEXPECTED_INDENT` | YAML 出现非预期缩进 |
| `FRONT_MATTER_REQUIRED_FIELD_MISSING` | 缺少必填字段 |
| `FRONT_MATTER_INVALID_FIELD_TYPE` | 字段类型错误 |
| `FRONT_MATTER_INVALID_DATETIME` | 时间格式错误或缺少时区 |
| `FRONT_MATTER_INVALID_TIME_ORDER` | `updated_at` 早于 `created_at` |
| `FRONT_MATTER_INVALID_ENUM` | 枚举值非法 |
| `FRONT_MATTER_INVALID_URL` | URL 非法 |
| `MARKDOWN_READ_ERROR` | Markdown 文件读取失败 |
| `MARKDOWN_DECODE_ERROR` | Markdown 文件编码错误 |

## 8. 后续衔接

TB-V10-005 产出的统一解析结果会作为 TB-V10-006 文档结构化数据模型的输入。
