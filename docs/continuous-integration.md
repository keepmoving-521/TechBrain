# TechBrain 持续集成流程

## 目标

CI 用于在代码进入主分支前自动执行安装、检查、测试和构建，保证后端、前端和本地基础设施配置始终处于可验证状态。

## 触发条件

工作流文件位于 `.github/workflows/ci.yml`。

触发条件：

- 推送到 `main` 分支
- 推送到 `master` 分支
- 面向 `main` 或 `master` 的 Pull Request
- 手动触发 `workflow_dispatch`

## 工作流组成

| Job | 作用 | 主要命令 |
| --- | --- | --- |
| Backend quality | 后端安装、静态检查、格式检查、单元测试、覆盖率检查、后端 wheel 构建 | `python -m ruff check .`、`python -m pytest ...`、`python -m pip wheel .` |
| Frontend quality and build | 前端安装、格式检查、Lint、类型检查、单元测试、生产构建 | `pnpm install --frozen-lockfile`、`pnpm check` |
| Compose configuration | 校验 Docker Compose 配置可解析 | `docker compose --env-file infra/local/.env.example config` |
| CI summary | 汇总关键 Job 状态，任一失败则整体失败 | shell 状态检查 |

## 构建产物

CI 会上传以下 artifacts：

- `techbrain-backend-wheel`：后端 wheel 包，来源于 `backend/dist/*.whl`
- `techbrain-frontend-dist`：前端生产构建产物，来源于 `frontend/dist`

这些产物可用于确认构建输出存在，也为后续发布流程保留接口。

## 失败定位

CI 将后端、前端和 Compose 配置拆分为独立 Job：

- 后端失败：优先查看 Ruff、格式检查、Pytest 或 wheel 构建步骤。
- 前端失败：优先查看 Prettier、ESLint、Vue TSC、Vitest 或 Vite build 步骤。
- Compose 失败：优先查看环境变量模板和 `compose.yaml` 的语法/变量配置。

## 本地等价检查

提交前建议在本地执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1
```

CI 仍是最终质量门禁，本地检查用于提前发现问题、减少远端流水线等待时间。
