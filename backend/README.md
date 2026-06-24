# TechBrain Backend

TechBrain 后端基础工程，基于 Python 3.12 与 FastAPI。

## 已提供能力

- `local`、`test`、`staging`、`production` 环境配置
- 环境变量和 `.env` 配置加载
- JSON 或控制台结构化日志
- 请求 ID 生成与透传
- 统一 HTTP、参数校验及未处理异常响应
- 存活检查和就绪检查
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
