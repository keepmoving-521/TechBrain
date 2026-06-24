# TechBrain 本地开发环境

本目录提供 TechBrain 本地开发所需基础依赖的 Docker Compose 使用说明。

## 前置要求

- Docker Desktop 或 Docker Engine
- Docker Compose v2
- 至少 4GB 可用内存；ElasticSearch 建议给 Docker 分配 2GB 以上内存

## 启动基础依赖

在项目根目录执行：

```powershell
Copy-Item infra/local/.env.example infra/local/.env
docker compose --env-file infra/local/.env up -d
```

启动后包含：

| 服务 | 地址 | 用途 |
| --- | --- | --- |
| MySQL | `127.0.0.1:3306` | 结构化业务数据 |
| Redis | `127.0.0.1:6379` | 异步任务 Broker、缓存和短期结果 |
| ElasticSearch | `http://127.0.0.1:9200` | 全文检索 |

## 查看健康状态

```powershell
docker compose --env-file infra/local/.env ps
```

也可以直接访问服务：

```powershell
docker exec techbrain-mysql mysqladmin ping -h 127.0.0.1 -uroot -ptechbrain_root
docker exec techbrain-redis redis-cli ping
Invoke-RestMethod http://127.0.0.1:9200/_cluster/health
```

## 初始化数据库迁移

基础服务健康后，在后端工程执行：

```powershell
cd backend
python -m techbrain.db.migrate upgrade head
```

后端默认数据库连接地址：

```text
mysql+pymysql://techbrain:techbrain@127.0.0.1:3306/techbrain?charset=utf8mb4
```

该地址与 `infra/local/.env.example` 中的本地 MySQL 默认值保持一致。

## 停止服务

```powershell
docker compose --env-file infra/local/.env stop
```

## 删除服务和数据卷

以下命令会删除 MySQL、Redis、ElasticSearch 的本地数据，请确认不再需要后执行：

```powershell
docker compose --env-file infra/local/.env down -v
```

## 配置与安全

- `infra/local/.env.example` 可以提交到仓库。
- `infra/local/.env` 用于本机覆盖端口和密码，已加入 `.gitignore`，不要提交。
- 当前配置仅用于本地开发，不要直接用于生产环境。
- ElasticSearch 本地开发关闭了安全认证；生产部署必须重新启用安全配置。
