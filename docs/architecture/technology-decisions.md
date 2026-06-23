# TechBrain 技术选型记录

> 需求编号：TB-V01-001  
> 文档状态：已确认  
> 决策日期：2026-06-23  
> 关联文档：[系统架构设计](system-architecture.md)

## 1. 选型原则

技术选型按以下优先级评估：

1. 满足 Markdown SSOT、可追溯和可重建要求。
2. 适合 Python 与 AI 生态，降低 V2.0 以后集成成本。
3. 适合单用户、单机部署，不过早承担分布式系统成本。
4. 社区成熟、文档完整、可测试、可替换。
5. 允许异步任务和数据组件按版本逐步启用。
6. 使用稳定主版本，实际开发时锁定精确依赖版本。

## 2. 决策摘要

| 编号 | 决策 | 结论 | 状态 |
| --- | --- | --- | --- |
| ADR-001 | 总体应用形态 | 模块化单体 + 独立 Worker | 已接受 |
| ADR-002 | 前端框架 | Vue 3 + TypeScript + Vite | 已接受 |
| ADR-003 | 前端组件与状态 | Element Plus + Pinia + Vue Router | 已接受 |
| ADR-004 | 后端框架 | Python 3.12 + FastAPI | 已接受 |
| ADR-005 | ORM 与迁移 | SQLAlchemy 2 + Alembic | 已接受 |
| ADR-006 | 异步任务 | Celery + Redis + Celery Beat | 已接受 |
| ADR-007 | 关系数据库 | MySQL 8.4 LTS | 已接受 |
| ADR-008 | 全文检索 | ElasticSearch 9.x + SmartCN | 已接受 |
| ADR-009 | 向量数据库 | Milvus Standalone，V2.0 启用 | 已接受 |
| ADR-010 | API 风格 | REST/JSON + OpenAPI + SSE | 已接受 |
| ADR-011 | 部署方式 | Linux Docker Compose + Nginx | 已接受 |
| ADR-012 | 数据一致性 | MySQL Outbox + 幂等任务 + 最终一致性 | 已接受 |
| ADR-013 | 知识图谱存储 | V3 初期使用 MySQL，不预设图数据库 | 已接受 |

## 3. ADR-001：模块化单体加独立 Worker

### 背景

TechBrain 既有在线查询，也有文件扫描、索引、向量化和 AI 任务。后者耗时较长，但当前产品是个人部署，不具备必须拆分微服务的团队或流量条件。

### 决策

- 后端使用单代码库和单业务数据库。
- API、Celery Worker、Celery Beat 使用同一应用代码构建。
- 运行时分为在线 API、异步 Worker 和调度器三个进程。
- 模块之间通过应用服务和领域事件协作。

### 选择理由

- 保留本地事务和低调试成本。
- Worker 可独立重启和扩容，不阻塞 API。
- 后续若出现明确需求，可沿模块边界拆分服务。

### 未选择

- 微服务：当前收益不足以抵消部署和一致性成本。
- 单进程后台线程：难以可靠重试、监控和独立扩缩。

## 4. ADR-002：Vue 3、TypeScript 和 Vite

### 决策

前端采用 Vue 3 Composition API、TypeScript 和 Vite。

### 选择理由

- Vue 3 适合知识管理类中后台页面和渐进式复杂交互。
- TypeScript 为 API 数据、图谱节点和 AI 流式事件提供类型约束。
- Vite 提供成熟的 Vue 开发与构建链路。
- V3.0 图谱和 V4.0 工作台可以在当前基础上扩展，无需更换框架。

### 未选择

- React：同样可行，但本项目不需要其生态特有能力；选定 Vue 后保持单一技术路线。
- Nuxt：TechBrain 当前不依赖 SEO 或服务端渲染，SPA 更简单。

## 5. ADR-003：Element Plus、Pinia 和 Vue Router

### 决策

- Element Plus 提供基础 UI 组件。
- Pinia 管理跨页面客户端状态。
- Vue Router 管理 SPA 路由。

### 选择理由

- Element Plus 适合表格、表单、树、对话框等知识管理场景。
- Pinia 是 Vue 生态中轻量且类型友好的状态方案。
- 不自研通用组件库，将精力放在 Markdown、搜索和 AI 体验上。

### 使用约束

- 服务端数据优先由请求层管理，不把所有接口结果长期塞入 Pinia。
- 业务组件不能直接依赖散落的 Element Plus 样式覆盖，应建立项目主题变量。

## 6. ADR-004：Python 3.12 和 FastAPI

### 决策

后端运行时基线采用 Python 3.12，Web 框架采用 FastAPI。

### 选择理由

- Python 与 Markdown 解析、Embedding、RAG 和 AI 生态天然衔接。
- FastAPI 基于类型注解生成 OpenAPI，适合前后端契约。
- 原生支持异步接口和 SSE 所需的流式响应模式。
- API 与 Worker 可以共享领域模型和模型适配器。
- Python 3.12 在项目启动时具有成熟的第三方库兼容性；不追逐刚发布的解释器版本。

### 未选择

- Django：管理后台和全栈能力强，但本项目采用独立 SPA，FastAPI 更轻且 API 导向更直接。
- Java/Spring Boot：工程能力成熟，但会增加与 Python AI 任务之间的双语言边界。

## 7. ADR-005：SQLAlchemy 2 和 Alembic

### 决策

- SQLAlchemy 2 负责关系数据访问。
- Alembic 负责数据库结构版本迁移。

### 选择理由

- 显式事务和成熟映射能力适合文档、标签、任务和 Outbox 数据。
- Alembic 可将每次结构变更纳入代码审查和发布流程。
- 避免业务代码绑定 MySQL 驱动的原始 SQL 细节。

### 使用约束

- 路由层不直接操作 ORM。
- 迁移脚本进入版本库，生产环境禁止使用自动建表替代迁移。
- 性能关键查询允许使用 SQLAlchemy Core 或受控原生 SQL。

## 8. ADR-006：Celery、Redis 和 Celery Beat

### 决策

- Celery 执行异步任务。
- Redis 作为消息代理和短期结果后端。
- Celery Beat 负责周期任务发布。

### 选择理由

- 文件扫描、全文索引和向量化天然适合任务队列。
- Celery 支持任务路由、重试、超时和多 Worker。
- Redis 在个人单机部署中较轻，兼顾短期缓存与锁。
- Celery 官方文档明确支持 Redis Broker 和周期任务。

### 风险与约束

- Redis 的 visibility timeout 可能导致长任务重复投递，因此业务任务必须幂等。
- 长期计划不能仅依赖 ETA 消息，应在 MySQL 中持久化计划。
- Beat 只能运行一个有效实例。
- Redis 不保存任务最终业务状态。

### 未选择

- FastAPI BackgroundTasks：适合短小的进程内任务，不适合全量同步、可靠重试和独立扩缩。
- Kafka：当前消息量和部署规模不需要流平台。
- RabbitMQ：是可靠的替代方案，但 Redis 的初期部署成本更低；若未来消息可靠性成为瓶颈，可保持 Celery 上层不变并更换 Broker。

## 9. ADR-007：MySQL 8.4 LTS

### 决策

结构化业务数据采用 MySQL 8.4 LTS。

### 选择理由

- 符合产品需求中既定的数据流。
- LTS 版本适合长期维护的个人部署。
- 能可靠承载文档元数据、用户行为、任务记录和 Outbox。
- 团队或个人已有 MySQL 技术积累时，运维和排错成本可控。

### 使用约束

- 默认字符集使用 `utf8mb4`。
- 时间以 UTC 保存。
- JSON 字段只用于低约束扩展信息，核心关联仍使用规范化表结构。
- 派生知识数据与不可重建的用户数据在模型和备份策略上明确区分。

### 未选择

- SQLite：开发轻便，但不适合作为 Celery 多进程和后续复杂查询的正式数据库。
- PostgreSQL：能力同样适合，但产品需求已确定 MySQL，当前没有足够收益支持偏离。

## 10. ADR-008：ElasticSearch 9.x 和 Smart Chinese Analysis

### 决策

- V1.0 全文检索采用 ElasticSearch 9.x。
- 中文及中英文混合内容优先评估官方 Smart Chinese Analysis 插件。
- 具体实现需求中通过检索样本决定字段级 analyzer；代码字段保留独立的低处理索引方式。

### 选择理由

- 支持全文相关度、字段权重、过滤、摘要和高亮。
- 与 V2.0 混合检索路线一致。
- 官方 SmartCN 插件提供简体中文和中英文混合文本分词，降低第三方插件版本风险。
- 索引别名和 Reindex 能支持无破坏重建。

### 风险与约束

- SmartCN 不可自定义，技术术语和专有词的效果需要通过评估集验证。
- 插件必须安装在每个节点，且版本与 ElasticSearch 完全一致。
- 若 SmartCN 无法满足技术词检索，再通过独立需求评估 IK、自定义词典或 n-gram 辅助字段。

### 未选择

- MySQL 全文索引：难以覆盖预期的高亮、复杂过滤和后续混合检索能力。
- 将 Milvus 同时作为全文搜索：向量检索不能替代精确关键词和代码检索。

## 11. ADR-009：Milvus Standalone

### 决策

V2.0 使用 Milvus Standalone 作为向量数据库，通过 Docker Compose Profile 按需启用。

### 选择理由

- 产品规划已将 Milvus 作为向量检索组件。
- 支持向量相似度搜索和标量元数据过滤。
- Standalone 形态符合个人部署，未来可迁移到集群或托管形态。

### 延迟启用理由

V1.0 不包含 Embedding 和语义检索。提前运行 Milvus 会增加内存、磁盘和运维开销，因此只在 V2.0 引入。

### 使用约束

- 集合必须记录模型版本和切片策略版本。
- 不在 Milvus 中保存唯一切片正文。
- Embedding 模型改变时建立新集合或新版本，不混用不同维度或语义空间。

## 12. ADR-010：REST、OpenAPI 和 SSE

### 决策

- 常规业务接口使用版本化 REST/JSON。
- FastAPI 生成 OpenAPI 契约。
- AI 回答流使用 Server-Sent Events。

### 选择理由

- CRUD、列表和任务状态查询使用 REST 足够清晰。
- OpenAPI 便于生成前端类型和接口文档。
- AI 回答主要是服务端单向推送，SSE 比 WebSocket 更简单。

### 未选择

- GraphQL：当前没有复杂多客户端数据聚合需求。
- 所有场景使用 WebSocket：增加连接管理成本，单向流式回答没有必要。

## 13. ADR-011：Docker Compose、Linux 和 Nginx

### 决策

- 正式个人部署使用 Linux Docker Compose。
- Nginx 提供静态文件、反向代理和统一入口。
- 本地 Windows 开发通过 Docker Desktop 运行基础依赖。

### 选择理由

- Compose 可以用一份声明管理 API、Worker、MySQL、Redis 和 ElasticSearch。
- 对个人部署而言，比 Kubernetes 更容易安装、备份和排错。
- Nginx 隐藏内部服务并处理静态资源和请求转发。

### 使用约束

- 镜像固定完整版本，禁止生产使用 `latest`。
- 数据卷和备份路径必须明确。
- 容器以非 root 用户运行，除非上游镜像存在不可避免限制。
- 数据库和搜索服务默认不映射公网端口。

## 14. ADR-012：Outbox 和最终一致性

### 决策

MySQL 与 ElasticSearch、Milvus 的同步采用事务 Outbox、幂等消费者和最终一致性。

### 选择理由

- MySQL 事务无法原子覆盖多个外部存储。
- 派生索引允许短暂延迟，但不能永久丢失更新。
- Outbox 使业务数据变化和待处理事件在同一事务中提交。
- 全量重建和一致性检查为最终兜底。

### 未选择

- 两阶段提交：外部组件支持和运维复杂度不适合本项目。
- “写数据库后直接写索引且不记录事件”：进程崩溃会永久遗漏更新。

## 15. ADR-013：V3 初期不引入图数据库

### 决策

V3.0 初期使用 MySQL 的实体表、关系表和递归查询实现知识图谱数据层；在真实规模和查询模式验证后再决定是否引入 Neo4j 等图数据库。

### 选择理由

- 个人知识图谱早期规模有限，主要查询是一至数层邻居和有限路径。
- 新增图数据库会增加备份、一致性和部署成本。
- 图谱展示不等于必须使用图数据库。

### 重新评估条件

出现以下任一情况时重新评估：

- 常用查询需要多跳复杂路径且 MySQL 无法满足性能目标。
- 实体和关系达到经测试确认的性能瓶颈。
- 图算法成为核心产品能力。
- 图数据需要独立扩缩或运维。

## 16. 版本维护策略

- Python、Node.js、MySQL 等运行时优先选择仍受支持的稳定或 LTS 版本。
- 应用依赖使用锁文件固定，不在文档中追逐每个补丁版本。
- 容器镜像固定完整标签，条件允许时固定 digest。
- 每次主版本升级建立独立需求，包含迁移、回滚和兼容测试。
- ElasticSearch 与所有插件保持完全相同的版本号。
- Milvus、SDK 和服务端版本按照官方兼容矩阵组合。

## 17. 待后续需求决定

以下内容不属于 TB-V01-001 的技术空白，而是已明确归属后续需求的详细设计：

| 事项 | 后续需求 |
| --- | --- |
| Markdown 目录及 Front Matter 字段 | TB-V10-001、TB-V10-002 |
| MySQL 表结构和索引 | TB-V10-006 等数据模型需求 |
| API 响应、分页和错误码 | TB-V01-008 |
| ElasticSearch Mapping 和字段权重 | TB-V10-034 |
| 同步任务参数、重试次数和超时 | TB-V10-011、TB-V10-047 |
| Embedding 模型和向量维度 | TB-V20-005、TB-V20-006 |
| LLM 厂商和具体模型 | TB-V20-015 |
| 是否引入图数据库 | V3.0 架构检查点 |
| Agent 权限矩阵 | TB-V40-021 |
