# TechBrain Markdown 文件扫描说明

本文说明 TechBrain 如何递归扫描 Markdown 知识库文件。

本能力对应 TB-V10-004，依赖 TB-V10-003 产出的知识库配置。

## 1. 职责边界

Markdown 文件扫描只负责发现可同步的 Markdown 文件，并记录扫描阶段遇到的路径错误。

本阶段不负责：

- 读取 Markdown 正文。
- 解析 Front Matter。
- 校验标题、标签、分类等元数据。
- 写入数据库或搜索索引。

这些能力会在后续文档解析和同步需求中实现。

## 2. 输入

扫描器使用后端配置模块生成的 `KnowledgeRepositoryConfig`：

```python
from techbrain.knowledge.config import build_knowledge_repository_config
from techbrain.knowledge.scanner import scan_markdown_files

config = build_knowledge_repository_config(settings)
result = scan_markdown_files(config)
```

扫描前必须先完成配置校验。如果配置错误，同步流程应拒绝执行，不进入扫描阶段。

## 3. 输出

扫描结果包含两部分：

| 字段 | 说明 |
| --- | --- |
| `files` | 符合规范、可进入后续解析阶段的 Markdown 文件 |
| `errors` | 扫描过程中发现的非致命路径错误 |

单个 Markdown 文件信息包含：

| 字段 | 说明 |
| --- | --- |
| `path` | 解析后的绝对真实路径 |
| `relative_path` | 相对知识库根目录的 POSIX 风格路径 |
| `size_bytes` | 文件大小 |

扫描错误信息包含：

| 字段 | 说明 |
| --- | --- |
| `path` | 出错路径 |
| `code` | 错误码 |
| `message` | 可记录到同步日志中的错误说明 |

## 4. 识别规则

扫描器遵循 [Markdown 知识目录规范](markdown-knowledge-spec.md)：

1. 从知识库根目录开始递归扫描。
2. 只识别 `.md` 文件。
3. 根目录下的 `README.md` 不作为知识文档同步。
4. 跳过 `assets/` 下的 Markdown 文件。
5. 默认跳过 `drafts/`，除非 `include_drafts=true`。
6. 默认跳过 `archive/`，除非 `include_archive=true`。
7. 跳过默认忽略规则和 `.techbrainignore` 命中的路径。
8. 解析后的真实路径必须仍位于知识库根目录内。
9. 超过 `max_file_size_bytes` 的 Markdown 文件不会进入文件列表，并记录错误。

## 5. 忽略规则

扫描器支持 `.gitignore` 常用子集：

```gitignore
tmp/
private/
*.tmp
*.secret.md
backend/generated/**
```

规则来源按以下顺序合并：

1. 系统默认忽略规则。
2. 知识根目录下的 `.techbrainignore`。
3. `TECHBRAIN_KNOWLEDGE_EXTRA_IGNORE_PATTERNS`。

匹配命中后，目录不会继续递归，文件不会进入扫描结果。

## 6. 错误记录

扫描过程中遇到不可访问路径或异常路径时，不会直接中断整个扫描，而是写入 `errors`。

当前错误码：

| 错误码 | 说明 |
| --- | --- |
| `DIRECTORY_ACCESS_ERROR` | 目录无法打开或遍历 |
| `PATH_ACCESS_ERROR` | 路径元信息无法读取 |
| `PATH_RESOLVE_ERROR` | 文件真实路径无法解析 |
| `PATH_OUTSIDE_ROOT` | 文件真实路径不在知识库根目录内 |
| `FILE_STAT_ERROR` | 文件状态无法读取 |
| `FILE_TOO_LARGE` | 文件超过配置的大小上限 |

同步任务可以根据这些错误生成扫描报告，提示用户修复目录权限、损坏路径或异常文件。

## 7. 示例

目录：

```text
TechBrain-Knowledge/
├── README.md
├── backend/
│   └── python/
│       └── sqlalchemy-joinedload.md
├── assets/
│   └── image-note.md
├── drafts/
│   └── draft-note.md
└── archive/
    └── old-note.md
```

默认配置下扫描结果：

```text
backend/python/sqlalchemy-joinedload.md
```

如果开启：

```text
TECHBRAIN_KNOWLEDGE_INCLUDE_DRAFTS=true
TECHBRAIN_KNOWLEDGE_INCLUDE_ARCHIVE=true
```

扫描结果会额外包含：

```text
archive/old-note.md
drafts/draft-note.md
```

`assets/image-note.md` 仍不会作为知识文档同步。

## 8. 后续衔接

TB-V10-004 只负责文件发现。

后续 TB-V10-005 会基于扫描出的 `files` 读取 Markdown 内容并解析 Front Matter、正文、标题层级、代码块和链接。
