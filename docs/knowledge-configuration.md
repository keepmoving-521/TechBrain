# TechBrain 知识库配置管理说明

## 1. 文档目的

本文说明 TechBrain 后端如何加载和校验 Markdown 知识库配置。

本能力对应 TB-V10-003，为后续 Markdown 文件扫描、解析和同步任务提供统一配置入口。

## 2. 配置来源

知识库配置通过后端 `Settings` 加载，遵循现有配置优先级：

1. 进程环境变量。
2. `backend/.env.{TECHBRAIN_ENVIRONMENT}`。
3. `backend/.env`。
4. 代码默认值。

所有配置项均使用 `TECHBRAIN_` 前缀。

## 3. 配置项

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `TECHBRAIN_KNOWLEDGE_ROOT` | 空 | Markdown 知识库根目录 |
| `TECHBRAIN_KNOWLEDGE_FILE_ENCODING` | `utf-8` | Markdown 和忽略文件编码 |
| `TECHBRAIN_KNOWLEDGE_IGNORE_FILE_NAME` | `.techbrainignore` | 忽略规则文件名 |
| `TECHBRAIN_KNOWLEDGE_EXTRA_IGNORE_PATTERNS` | 空 | 额外忽略规则，逗号分隔 |
| `TECHBRAIN_KNOWLEDGE_INCLUDE_DRAFTS` | `false` | 是否包含 `drafts/` |
| `TECHBRAIN_KNOWLEDGE_INCLUDE_ARCHIVE` | `false` | 是否包含 `archive/` |
| `TECHBRAIN_KNOWLEDGE_SYNC_BATCH_SIZE` | `100` | 单批同步文档数量 |
| `TECHBRAIN_KNOWLEDGE_MAX_FILE_SIZE_BYTES` | `5242880` | 单个 Markdown 文件最大字节数 |

示例：

```env
TECHBRAIN_KNOWLEDGE_ROOT=D:\Knowledge\TechBrain
TECHBRAIN_KNOWLEDGE_FILE_ENCODING=utf-8
TECHBRAIN_KNOWLEDGE_IGNORE_FILE_NAME=.techbrainignore
TECHBRAIN_KNOWLEDGE_EXTRA_IGNORE_PATTERNS=private/,*.secret.md
TECHBRAIN_KNOWLEDGE_INCLUDE_DRAFTS=false
TECHBRAIN_KNOWLEDGE_INCLUDE_ARCHIVE=false
TECHBRAIN_KNOWLEDGE_SYNC_BATCH_SIZE=100
TECHBRAIN_KNOWLEDGE_MAX_FILE_SIZE_BYTES=5242880
```

## 4. 同步前校验

后端提供同步前配置校验入口：

```python
from techbrain.core.config import get_settings
from techbrain.knowledge.config import build_knowledge_repository_config

settings = get_settings()
knowledge_config = build_knowledge_repository_config(settings)
```

当配置不满足同步要求时，会抛出：

```python
KnowledgeConfigurationError
```

同步任务必须在扫描文件前调用该方法。如果抛出异常，应拒绝执行同步，并把错误消息记录到同步任务失败原因中。

## 5. 校验规则

### 5.1 知识根目录

`TECHBRAIN_KNOWLEDGE_ROOT` 必须：

- 已配置。
- 路径存在。
- 是目录而不是文件。
- 解析后的真实路径可作为扫描根目录。

错误示例：

```text
TECHBRAIN_KNOWLEDGE_ROOT=
```

错误消息：

```text
知识库根目录未配置, 请设置 TECHBRAIN_KNOWLEDGE_ROOT
```

### 5.2 文件编码

当前支持：

```text
utf-8
utf-8-sig
```

`.techbrainignore` 必须能使用该编码读取。

### 5.3 忽略文件名

`TECHBRAIN_KNOWLEDGE_IGNORE_FILE_NAME` 必须是文件名，不能包含路径分隔符。

正确：

```text
.techbrainignore
```

错误：

```text
config/.techbrainignore
```

### 5.4 忽略规则

忽略规则来源：

1. 系统默认忽略规则。
2. 知识根目录下的 `.techbrainignore`。
3. `TECHBRAIN_KNOWLEDGE_EXTRA_IGNORE_PATTERNS`。

默认忽略规则包括：

```text
.git/
.idea/
.vscode/
node_modules/
dist/
build/
tmp/
temp/
.DS_Store
Thumbs.db
*.tmp
*.bak
*.swp
~$*
```

`.techbrainignore` 支持：

- 空行。
- `#` 注释。
- 目录规则，例如 `private/`。
- 通配符规则，例如 `*.secret.md`。

### 5.5 同步参数

`TECHBRAIN_KNOWLEDGE_SYNC_BATCH_SIZE`：

- 最小值：`1`
- 最大值：`1000`

`TECHBRAIN_KNOWLEDGE_MAX_FILE_SIZE_BYTES`：

- 最小值：`1024`
- 默认值：`5242880`

## 6. 配置变更加载

配置变更通过重新加载 `Settings` 生效。

在运行进程中，如果需要重新读取环境变量，应清除配置缓存：

```python
from techbrain.core.config import get_settings

get_settings.cache_clear()
settings = get_settings()
```

后续如提供管理接口或同步任务调度器，应在启动新同步任务前读取最新配置或显式刷新配置。

## 7. 与规范文档的关系

相关规范：

- [Markdown 知识目录规范](markdown-knowledge-spec.md)
- [Front Matter 元数据规范](front-matter-spec.md)

TB-V10-003 只负责配置加载和同步前校验，不负责递归扫描文件。文件扫描将在 TB-V10-004 中实现。

## 8. 后续开发检查清单

实现同步任务时必须确认：

- [ ] 调用 `build_knowledge_repository_config()`。
- [ ] 配置错误时拒绝执行同步。
- [ ] 错误消息写入同步任务失败原因。
- [ ] 扫描根目录使用校验后的 `root`。
- [ ] 文件读取使用校验后的 `file_encoding`。
- [ ] 忽略规则使用合并后的 `ignore_patterns`。
- [ ] 草稿和归档是否参与扫描遵循 `include_drafts` 和 `include_archive`。
- [ ] 批处理数量遵循 `sync_batch_size`。
- [ ] 文件大小限制遵循 `max_file_size_bytes`。
