# 定时同步说明

本文档对应 TB-V10-014：实现定时同步。

## 1. 目标

系统支持按配置周期自动执行 Markdown 知识库全量同步，用于让知识库在后台持续保持最新。

定时同步复用 TB-V10-011 的全量同步能力和 TB-V10-012 的同步任务记录能力。

## 2. 配置项

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `TECHBRAIN_KNOWLEDGE_AUTO_SYNC_ENABLED` | `false` | 是否在应用启动后启用定时同步 |
| `TECHBRAIN_KNOWLEDGE_AUTO_SYNC_INTERVAL_SECONDS` | `3600` | 同步周期，单位秒，最小值为 `60` |

示例：

```env
TECHBRAIN_KNOWLEDGE_AUTO_SYNC_ENABLED=true
TECHBRAIN_KNOWLEDGE_AUTO_SYNC_INTERVAL_SECONDS=1800
```

## 3. 执行机制

后端应用启动时会创建知识同步调度器。

当定时同步启用后，调度器会按当前周期触发一次全量同步：

```text
应用启动
  ↓
读取定时同步配置
  ↓
启动后台调度线程
  ↓
按周期触发全量同步
  ↓
记录同步任务与失败详情
```

## 4. 并发控制

定时同步与手动同步共享同一把同步锁。

如果某个知识库同步任务正在执行：

- 手动同步会返回 `409 CONFLICT`。
- 定时同步会跳过本轮执行，并在调度器运行状态中记录最近错误。

这样可以避免同一知识库出现重叠执行、重复写入或状态互相覆盖。

## 5. 失败记录

定时同步失败需要可追踪。

当前实现中：

- Markdown 扫描失败、解析失败、同步失败会进入同步任务失败明细。
- 知识库配置错误会创建一条失败同步任务，失败阶段为 `configuration`。
- 单个文档失败不会阻塞其他文档处理。

配置错误记录示例：

```json
{
  "status": "failed",
  "scanned_count": 0,
  "failed_count": 1,
  "failures": [
    {
      "path": "-",
      "stage": "configuration",
      "code": "KNOWLEDGE_CONFIGURATION_ERROR",
      "message": "TECHBRAIN_KNOWLEDGE_ROOT 未配置"
    }
  ]
}
```

## 6. 管理接口

### 6.1 查询定时同步配置

```http
GET /api/v1/knowledge/sync/schedule
```

响应示例：

```json
{
  "enabled": false,
  "interval_seconds": 3600,
  "running": false,
  "last_started_at": null,
  "last_finished_at": null,
  "last_task_id": null,
  "last_error": null
}
```

### 6.2 修改定时同步配置

```http
PUT /api/v1/knowledge/sync/schedule
Content-Type: application/json

{
  "enabled": true,
  "interval_seconds": 1800
}
```

响应示例：

```json
{
  "enabled": true,
  "interval_seconds": 1800,
  "running": false,
  "last_started_at": null,
  "last_finished_at": null,
  "last_task_id": null,
  "last_error": null
}
```

## 7. 前端页面

同步管理页面增加“定时同步”配置区，支持：

- 查看当前启用状态。
- 修改同步周期。
- 启用或停用定时同步。
- 查看最近执行时间、最近任务和最近错误。

## 8. 验收结论

TB-V10-014 已覆盖以下验收点：

- 可启用、停用和修改周期。
- 同一知识库不会重叠执行。
- 失败会进入同步任务记录或调度器状态。
