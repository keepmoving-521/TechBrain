# TechBrain 代码质量检查规范

## 目标

本规范定义 TechBrain 本地开发、提交前和后续 CI 使用的统一质量检查入口，确保后端、前端代码在格式、静态检查、类型检查、单元测试和构建方面保持一致。

## 根目录统一入口

在项目根目录执行完整检查：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1
```

仅检查后端：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1 -BackendOnly
```

仅检查前端：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1 -FrontendOnly
```

提交前检查命令：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\pre-commit.ps1
```

## 后端检查

后端位于 `backend/`，质量检查包括：

```powershell
python -m ruff check .
python -m ruff format --check .
python -m pytest --cov=techbrain --cov-report=term-missing
```

规则来源：

- Ruff 负责静态检查和格式检查。
- Pytest 负责单元测试。
- Coverage 最低覆盖率要求为 90%。
- Ruff 规则配置位于 `backend/pyproject.toml`。

## 前端检查

前端位于 `frontend/`，统一入口：

```powershell
pnpm check
```

该命令会依次执行：

```powershell
pnpm format:check
pnpm lint
pnpm type-check
pnpm test
pnpm build
```

规则来源：

- Prettier 负责格式检查。
- ESLint 负责静态检查。
- Vue TSC 负责 TypeScript 与 Vue 类型检查。
- Vitest 负责前端单元测试。
- Vite build 负责生产构建验证。

## 开发时自动修复

后端格式化：

```powershell
cd backend
python -m ruff format .
python -m ruff check . --fix
```

前端格式化：

```powershell
cd frontend
pnpm format
```

## 失败处理原则

- 格式失败：先运行格式化命令，再重新检查。
- 静态检查失败：优先修复规则指出的问题，不随意关闭规则。
- 测试失败：先确认是否为业务逻辑变化；若需求变化导致断言失效，应同步更新测试。
- 覆盖率失败：为新增关键逻辑补充测试，而不是降低覆盖率门槛。
- 构建失败：优先修复类型、模块解析和环境变量问题。
