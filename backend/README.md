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

V0.1 当前只建立迁移机制和基线版本，业务表会在后续需求中逐步加入。

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
