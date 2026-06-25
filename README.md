# TechBrain

TechBrain 是一个面向程序员的个人技术知识资产管理平台，用于统一沉淀、管理、检索、关联和利用个人在学习、工作与项目实践中积累的技术知识。

项目以 Markdown 作为知识唯一事实来源（SSOT），逐步建设个人技术百科、全文搜索引擎、RAG 知识库、知识图谱与 AI 学习助手。

## 核心能力

- Markdown 知识同步与结构化管理
- 分类、标签、关联与知识浏览
- ElasticSearch 全文检索
- 基于个人知识库的 AI 问答
- 知识图谱与关联推荐
- AI 学习路线、总结、补全和推荐

## 版本路线

| 版本 | 主题 | 核心成果 |
| --- | --- | --- |
| V1.0 | 知识管理平台 | 形成统一、可浏览、可检索的技术知识库 |
| V2.0 | AI 知识问答 | 支持带来源引用的个人知识库 RAG 问答 |
| V3.0 | 知识图谱平台 | 形成可视化的技术知识关联网络 |
| V4.0 | AI 学习助手 | 提供个性化、可持续的技术学习辅助 |

## 项目文档

- [产品需求与版本规划](docs/product-requirements.md)
- [系统版本迭代计划](docs/version-iteration-plan.md)
- [系统架构设计](docs/architecture/system-architecture.md)
- [技术选型记录](docs/architecture/technology-decisions.md)
- [API 基础规范](docs/api-guidelines.md)
- [Markdown 知识目录规范](docs/markdown-knowledge-spec.md)
- [Front Matter 元数据规范](docs/front-matter-spec.md)
- [知识库配置管理说明](docs/knowledge-configuration.md)
- [Markdown 文件扫描说明](docs/markdown-scanning.md)
- [Markdown 内容解析说明](docs/markdown-parsing.md)
- [文档结构化数据模型说明](docs/knowledge-document-data-model.md)
- [代码质量检查规范](docs/development-quality-checks.md)
- [持续集成流程](docs/continuous-integration.md)

## 工程入口

- [后端开发与运行说明](backend/README.md)
- [前端开发与运行说明](frontend/README.md)
- [本地开发环境说明](infra/local/README.md)

## 质量检查

完整检查：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1
```

提交前检查：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\pre-commit.ps1
```

## 持续集成

仓库提供 GitHub Actions 工作流：

```text
.github/workflows/ci.yml
```

推送到 `main` / `master` 或创建 Pull Request 时，会自动执行后端检查、前端检查、Compose 配置校验，并上传后端 wheel 与前端 dist 构建产物。

## 当前状态

项目已完成系统架构设计、后端基础工程、前端基础工程、数据库迁移机制、本地开发环境编排、代码质量检查机制与持续集成流程，正在进行 V0.1 基础版本开发。
