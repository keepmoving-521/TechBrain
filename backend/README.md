# TechBrain Backend

TechBrain 后端基础工程，基于 Python 3.12 与 FastAPI。

## 已提供能力

- `local`、`test`、`staging`、`production` 环境配置
- 环境变量和 `.env` 配置加载
- JSON 或控制台结构化日志
- 请求 ID 生成与透传
- 统一 HTTP、参数校验及未处理异常响应
- 存活检查和就绪检查
- MySQL 数据库配置、连接管理和 Alembic 迁移机制
- Markdown 知识库配置加载与同步前校验
- Markdown 知识目录递归扫描与错误记录
- Markdown Front Matter、正文结构、代码块和链接解析
- Markdown 文档结构化数据模型与数据库迁移
- Markdown 新增文档同步入库
- Markdown 修改文档同步更新
- Markdown 文档移动识别
- Markdown 文档软删除与恢复
- Markdown 知识库全量同步任务
- Markdown 同步任务记录与失败明细
- Markdown 手动触发同步管理接口
- Markdown 定时同步及调度配置接口
- 层级分类模型、同步、查询、管理、删除与文档迁移
- 标签模型、同步、查询、管理与合并
- 文档分页筛选、知识首页聚合及文档详情 API
- Pytest 测试与 Ruff 代码检查

## 环境要求

- Python 3.12

## 本地启动

```powershell
cd backend
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m uvicorn techbrain.main:app --reload
```

默认访问地址：

- API 文档：<http://127.0.0.1:8000/docs>
- 存活检查：<http://127.0.0.1:8000/api/v1/health/live>
- 就绪检查：<http://127.0.0.1:8000/api/v1/health/ready>

## 数据库迁移

后端默认使用 MySQL，连接地址通过 `TECHBRAIN_DATABASE_URL` 配置：

```text
TECHBRAIN_DATABASE_URL=mysql+pymysql://techbrain:techbrain@127.0.0.1:3306/techbrain?charset=utf8mb4
```

初始化空数据库或升级到最新结构：

```powershell
python -m techbrain.db.migrate upgrade head
```

查看当前数据库版本：

```powershell
python -m techbrain.db.migrate current
```

查看迁移历史：

```powershell
python -m techbrain.db.migrate history
```

当前迁移已推进到 `0007`，包含文档、同步任务与失败记录、层级分类、标签及文档标签关联等业务表。完整迁移清单见：[数据库迁移说明](migrations/README.md)。

应用就绪检查会执行轻量数据库连接检测：

```text
GET /api/v1/health/ready
```

数据库不可用时，该接口返回 `503`，并在 `checks` 中标记 `database` 为 `error`。

## Markdown 知识库配置

知识库同步前会从后端配置中加载 Markdown 知识源参数，并先执行配置校验。配置不合法时，同步流程应拒绝执行并返回明确原因。

常用配置项：

```text
TECHBRAIN_KNOWLEDGE_ROOT=C:\Users\87996\Documents\TechBrainKnowledge
TECHBRAIN_KNOWLEDGE_FILE_ENCODING=utf-8
TECHBRAIN_KNOWLEDGE_IGNORE_FILE_NAME=.techbrainignore
TECHBRAIN_KNOWLEDGE_EXTRA_IGNORE_PATTERNS=private/**,*.secret.md
TECHBRAIN_KNOWLEDGE_INCLUDE_DRAFTS=false
TECHBRAIN_KNOWLEDGE_INCLUDE_ARCHIVE=false
TECHBRAIN_KNOWLEDGE_SYNC_BATCH_SIZE=100
TECHBRAIN_KNOWLEDGE_MAX_FILE_SIZE_BYTES=5242880
```

当前校验范围包括：

- 知识库根目录必须配置、存在且为目录
- 文件编码仅支持 `utf-8` 和 `utf-8-sig`
- 忽略规则文件名不能为空，且不能包含路径分隔符
- 忽略规则文件必须可按配置编码读取
- 同步批大小和单文件大小上限必须落在允许范围内

完整约定见：[知识库配置管理说明](../docs/knowledge-configuration.md)。

## Markdown 文件扫描

后端提供 Markdown 文件扫描器，用于从校验后的知识库根目录递归发现可同步文档。

扫描规则：

- 只识别 `.md` 文件
- 跳过根目录 `README.md`
- 跳过 `assets/`、默认忽略目录和 `.techbrainignore` 命中路径
- 默认跳过 `drafts/` 和 `archive/`，可通过配置显式包含
- 路径不可访问、真实路径越界或文件过大时记录错误，不直接中断整个扫描

完整约定见：[Markdown 文件扫描说明](../docs/markdown-scanning.md)。

## Markdown 内容解析

后端提供 Markdown 内容解析器，用于把扫描得到的 Markdown 文件转换为统一解析结果。

解析范围：

- Front Matter 字段和基础校验
- Markdown 正文
- 标题层级
- 围栏代码块
- Markdown 内联链接

格式错误会返回包含文件路径、错误码、字段名、行号和列号的错误信息，便于同步任务记录失败原因。

完整约定见：[Markdown 内容解析说明](../docs/markdown-parsing.md)。

## 文档结构化数据模型

后端提供 `knowledge_documents` 表和对应 ORM 模型，用于保存 Markdown 知识文档的最新结构化状态。

模型支持：

- 通过 `document_id` 保持文档稳定身份
- 通过 `relative_path`、`absolute_path` 和 `path_hash` 记录文件移动
- 通过 `content_hash` 和 `front_matter_hash` 判断内容或元数据变化
- 通过 `is_deleted` 和 `deleted_at` 支持软删除
- 通过 `sync_status`、`sync_error`、`last_scanned_at`、`last_synced_at` 记录同步状态

完整约定见：[文档结构化数据模型说明](../docs/knowledge-document-data-model.md)。

## 新增文档同步

后端提供新增文档同步服务，用于将首次扫描到的合法 Markdown 文档写入 `knowledge_documents`。

同步规则：

- 解析失败时不入库，并返回具体解析错误
- 新文档成功入库后 `sync_status=synced`
- 正文写入 `body`
- 元数据写入 Front Matter 对应结构化字段
- 根据 `document_id` 和 `relative_path` 保证重复同步不重复插入

完整约定见：[新增文档同步说明](../docs/knowledge-new-document-sync.md)。

## 修改文档同步

后端提供通用文档同步服务，用于识别已存在 Markdown 文档的正文或元数据变化，并更新同一条 `knowledge_documents` 记录。

同步规则：

- 通过 `path_hash`、`content_hash`、`front_matter_hash` 判断变化
- 未变化文档返回 `unchanged`，不重复更新数据库记录
- 正文变化时更新 `body` 和 `content_hash`
- 元数据变化时更新 Front Matter 对应结构化字段和 `front_matter_hash`
- 更新成功后刷新 `last_scanned_at` 和 `last_synced_at`

完整约定见：[修改文档同步说明](../docs/knowledge-update-document-sync.md)。

## 文档移动识别

同步服务通过 Front Matter `id` 识别文档稳定身份。文件路径变化但 `document_id` 不变时，会更新同一条 `knowledge_documents` 记录，而不是新增一条记录。

移动识别规则：

- 优先按 `document_id` 查找已有文档
- 同一 `document_id` 的新路径会更新 `relative_path`、`absolute_path` 和 `path_hash`
- 数据库主键和 `document_id` 保持不变
- 新路径已被其他文档占用时返回 `DOCUMENT_PATH_CONFLICT`

完整约定见：[文档移动识别说明](../docs/knowledge-move-document-sync.md)。

## 文档删除与恢复

同步服务支持在源 Markdown 文件缺失时将文档标记为软删除，并在文件恢复后重新激活原文档记录。

同步规则：

- 本轮扫描未出现的活动文档会被标记为 `is_deleted=true`
- 软删除文档的 `sync_status=deleted`
- 正常列表和搜索应使用 `active_knowledge_documents_statement()` 过滤 `is_deleted=false`
- 文件恢复且 `document_id` 不变时复用原数据库主键
- 恢复后清空 `deleted_at`，并将 `sync_status` 改回 `synced`

完整约定见：[文档删除与恢复同步说明](../docs/knowledge-delete-restore-sync.md)。

## 全量同步任务

后端提供全量同步任务编排函数，用于一次性处理整个 Markdown 知识库。

任务流程：

- 扫描知识库目录
- 逐个解析并同步 Markdown 文档
- 自动处理新增、修改、移动和恢复
- 本轮扫描缺失的活动文档会被软删除
- 单个文档失败会记录失败明细，不阻塞其他文档
- 重复执行时未变化文档返回 `unchanged`

完整约定见：[全量同步任务说明](../docs/knowledge-full-sync-task.md)。

## 同步任务记录

后端提供同步任务记录模型，用于保存每次全量同步的执行结果和失败详情。

记录内容：

- 任务开始时间和结束时间
- 扫描数量、成功数量和失败数量
- 新增、修改、恢复、未变化和软删除数量
- 失败文件路径、阶段、错误码、字段、行号和列号

全量同步默认会写入 `knowledge_sync_tasks` 和 `knowledge_sync_failures`；当前任务列表与详情接口直接基于这些记录查询同步历史。

完整约定见：[同步任务记录说明](../docs/knowledge-sync-task-record.md)。

## 手动触发同步

后端提供知识库同步管理接口：

```text
POST /api/v1/knowledge/sync
GET /api/v1/knowledge/sync/tasks
GET /api/v1/knowledge/sync/tasks/{task_id}
```

重复触发同步时，后端通过进程内同步锁避免并发任务冲突；已有任务执行中会返回 `409`。

完整约定见：[手动触发同步说明](../docs/knowledge-manual-sync.md)。

## 定时同步

后端支持按配置周期自动执行 Markdown 知识库同步。定时同步与手动同步共享同步锁，避免同一知识库重叠执行；配置错误、扫描失败、解析失败和同步失败均会被记录到同步任务或调度器状态中。

相关配置：

```env
TECHBRAIN_KNOWLEDGE_AUTO_SYNC_ENABLED=false
TECHBRAIN_KNOWLEDGE_AUTO_SYNC_INTERVAL_SECONDS=3600
```

管理接口：

- `GET /api/v1/knowledge/sync/schedule`
- `PUT /api/v1/knowledge/sync/schedule`

完整约定见：[定时同步说明](../docs/knowledge-scheduled-sync.md)。

## 分类、标签与知识查询 API

当前后端已提供以下知识管理接口：

```text
GET    /api/v1/knowledge/overview
GET    /api/v1/documents
GET    /api/v1/documents/{id}
GET    /api/v1/categories/tree
GET    /api/v1/categories/{id}
POST   /api/v1/categories
PATCH  /api/v1/categories/{id}
DELETE /api/v1/categories/{id}
GET    /api/v1/tags
GET    /api/v1/tags/{id}
POST   /api/v1/tags
PATCH  /api/v1/tags/{id}
DELETE /api/v1/tags/{id}
```

分类还支持文档迁移，标签支持关联文档查询与标签合并。接口字段、分页和错误语义详见[文档中心](../docs/README.md)。

## 配置优先级

配置按以下优先级加载，越靠前优先级越高：

1. 进程环境变量
2. `backend/.env.{TECHBRAIN_ENVIRONMENT}`
3. `backend/.env`
4. 代码默认值

所有配置项使用 `TECHBRAIN_` 前缀。仓库只提交 `.env.example`，真实 `.env` 不得提交。

生产环境具有额外保护：

- `TECHBRAIN_DEBUG` 必须为 `false`
- `TECHBRAIN_LOG_FORMAT` 必须为 `json`
- `TECHBRAIN_LOG_LEVEL` 不能为 `DEBUG`

## 常用命令

```powershell
# 执行测试
python -m pytest

# 执行测试并检查覆盖率
python -m pytest --cov=techbrain --cov-report=term-missing

# 静态检查
python -m ruff check .

# 格式检查
python -m ruff format --check .
```

也可以在项目根目录执行统一质量检查：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1 -BackendOnly
```

## 错误响应

所有 API 错误统一返回：

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "请求参数校验失败",
    "details": []
  },
  "request_id": "d5315d67361b4e24a337081b64cdf80e"
}
```

响应头同时包含 `X-Request-ID`，调用方也可传入该请求头用于链路关联。

完整 API 约定见：[API 基础规范](../docs/api-guidelines.md)。
