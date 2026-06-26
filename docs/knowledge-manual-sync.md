# TechBrain 手动触发同步说明

本文说明 TechBrain 如何通过管理接口和前端页面手动发起 Markdown 知识库同步。

本能力对应 TB-V10-013，依赖：

- TB-V10-011：全量同步任务。
- TB-V10-012：同步任务记录。

## 1. 能力范围

手动同步支持：

- 用户在前端页面点击按钮触发同步。
- 后端执行一次全量同步任务。
- 同步完成后返回任务结果。
- 页面展示同步历史、统计结果和失败详情。
- 重复点击时通过互斥锁避免并发同步冲突。

本阶段采用进程内同步锁和同步执行方式。后续如果引入 Celery、RQ 或独立 Worker，可复用现有任务记录表和接口响应结构。

## 2. 后端接口

### 2.1 触发同步

```http
POST /api/v1/knowledge/sync
```

成功响应：

```json
{
  "id": 1,
  "status": "success",
  "started_at": "2026-06-26T09:00:00Z",
  "finished_at": "2026-06-26T09:00:01Z",
  "scanned_count": 10,
  "success_count": 10,
  "failed_count": 0,
  "created_count": 2,
  "updated_count": 1,
  "restored_count": 0,
  "unchanged_count": 7,
  "deleted_count": 0,
  "failures": []
}
```

配置错误：

```http
400 Bad Request
```

例如知识库根目录未配置。

并发冲突：

```http
409 Conflict
```

表示已有同步任务正在执行，前端应提示用户稍后再试。

### 2.2 查询任务列表

```http
GET /api/v1/knowledge/sync/tasks
```

响应：

```json
{
  "items": []
}
```

### 2.3 查询任务详情

```http
GET /api/v1/knowledge/sync/tasks/{task_id}
```

任务不存在：

```http
404 Not Found
```

## 3. 前端页面

新增页面：

```text
/system/sync
```

页面名称：

```text
同步管理
```

页面能力：

- 点击“立即同步”触发后端同步。
- 点击“刷新记录”拉取任务历史。
- 展示最近一次同步摘要。
- 展示任务列表。
- 点击任务行查看任务详情。
- 展示失败文件、阶段、错误码、字段、行号、列号和说明。

## 4. 并发控制

后端在应用进程内维护同步锁：

```text
knowledge_sync_lock
```

触发同步时：

1. 尝试获取锁。
2. 获取成功则执行全量同步。
3. 获取失败则返回 `409 Conflict`。
4. 同步完成或异常后释放锁。

这样可以避免重复点击导致同一进程内出现多个冲突同步任务。

## 5. 后续衔接

TB-V10-013 已完成手动触发入口和页面操作。

后续可以继续增强：

- 异步后台任务执行。
- 任务执行中状态轮询。
- 分布式锁。
- 任务取消。
- 失败重试。
