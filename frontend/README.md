# TechBrain Frontend

TechBrain 前端基础工程，基于 Vue 3、TypeScript、Vite、Vue Router、Pinia 和 Element Plus。

## 本地启动

```powershell
cd frontend
pnpm install
pnpm dev
```

访问：

- 前端应用：<http://127.0.0.1:5173>
- 系统状态页：<http://127.0.0.1:5173/system/status>

## 后端代理

开发环境默认将 `/api` 代理到：

```text
http://127.0.0.1:8000
```

前端 API Base URL 默认为：

```text
/api/v1
```

因此健康检查请求会访问：

```text
/api/v1/health/live
```

如需修改后端地址，可复制 `.env.example` 为 `.env.local` 后调整：

```text
VITE_BACKEND_ORIGIN=http://127.0.0.1:8000
```

## 常用命令

```powershell
pnpm dev
pnpm type-check
pnpm build
pnpm preview
```

## 已包含能力

- 基础应用布局
- Vue Router history 路由
- Dashboard、知识库、搜索、系统状态和 404 页面
- Axios 请求封装
- 统一 API 错误提示
- 基础主题变量和全局样式
- Vite 开发服务器刷新 fallback
