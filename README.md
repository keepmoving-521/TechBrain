# TechBrain

TechBrain 是一个面向程序员的个人技术知识资产管理平台，用于统一沉淀、管理、检索、关联和利用个人在学习、工作与项目实践中积累的技术知识。

项目以 Markdown 作为知识唯一事实来源（SSOT），逐步建设个人技术百科、全文搜索引擎、RAG 知识库、知识图谱与 AI 学习助手。

## 当前已实现

- Markdown 扫描、解析、全量同步、移动识别、软删除与恢复
- 手动同步、定时同步、任务记录和失败明细
- 文档、层级分类、标签及关联关系的结构化存储
- 分类和标签管理、查询、合并及安全回写
- 知识首页、分类/标签知识浏览、分页排序
- 文档列表和完整详情 API

全文检索、RAG 问答、知识图谱和 AI 学习助手属于后续版本路线，尚未交付。

## 版本路线

| 版本 | 主题 | 核心成果 |
| --- | --- | --- |
| V1.0 | 知识管理平台 | 形成统一、可浏览、可检索的技术知识库 |
| V2.0 | AI 知识问答 | 支持带来源引用的个人知识库 RAG 问答 |
| V3.0 | 知识图谱平台 | 形成可视化的技术知识关联网络 |
| V4.0 | AI 学习助手 | 提供个性化、可持续的技术学习辅助 |

## 项目文档

- [文档中心与交付索引](docs/README.md)
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
- [新增文档同步说明](docs/knowledge-new-document-sync.md)
- [修改文档同步说明](docs/knowledge-update-document-sync.md)
- [文档移动识别说明](docs/knowledge-move-document-sync.md)
- [文档删除与恢复同步说明](docs/knowledge-delete-restore-sync.md)
- [全量同步任务说明](docs/knowledge-full-sync-task.md)
- [同步任务记录说明](docs/knowledge-sync-task-record.md)
- [手动触发同步说明](docs/knowledge-manual-sync.md)
- [定时同步说明](docs/knowledge-scheduled-sync.md)
- [分类数据模型说明](docs/knowledge-category-data-model.md)
- [Markdown 文档分类同步说明](docs/knowledge-category-sync.md)
- [分类查询接口说明](docs/knowledge-category-query.md)
- [分类管理说明](docs/knowledge-category-management.md)
- [分类删除与文档迁移说明](docs/knowledge-category-delete-migration.md)
- [标签数据模型说明](docs/knowledge-tag-data-model.md)
- [Markdown 文档标签同步说明](docs/knowledge-tag-sync.md)
- [标签查询接口说明](docs/knowledge-tag-query.md)
- [标签管理说明](docs/knowledge-tag-management.md)
- [标签合并说明](docs/knowledge-tag-merge.md)
- [文档列表接口说明](docs/knowledge-document-list.md)
- [知识首页说明](docs/knowledge-homepage.md)
- [分类知识列表页说明](docs/category-knowledge-list.md)
- [标签知识列表页说明](docs/tag-knowledge-list.md)
- [文档详情接口说明](docs/knowledge-document-detail.md)
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

- V0.1 项目基础版本：TB-V01-001～008 已完成。
- V1.0 知识管理平台：TB-V10-001～029 已完成。
- 当前能力覆盖 Markdown 知识同步、分类标签管理、知识首页、分类/标签浏览及文档详情 API。
- 下一项计划需求：TB-V10-030 Markdown 安全渲染。

详细状态以[系统版本迭代计划](docs/version-iteration-plan.md)为准。
