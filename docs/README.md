# TechBrain 文档中心

本页是项目文档的统一导航与交付索引。需求完成状态以[系统版本迭代计划](version-iteration-plan.md)为准；具体实现契约以对应专题文档、代码和自动化测试为准。

## 当前进度

| 阶段 | 完成范围 | 当前状态 |
| --- | --- | --- |
| V0.1 项目基础版本 | TB-V01-001～008 | 已完成 |
| V1.0 知识管理平台 | TB-V10-001～029 | 持续迭代 |
| 当前下一项 | TB-V10-030 Markdown 安全渲染 | 待开发 |

最后核对日期：2026-06-29。

## 产品与计划

- [产品需求与版本规划](product-requirements.md)
- [系统版本迭代计划](version-iteration-plan.md)

## 架构与工程规范

- [系统架构设计](architecture/system-architecture.md)
- [技术选型记录](architecture/technology-decisions.md)
- [API 基础规范](api-guidelines.md)
- [代码质量检查规范](development-quality-checks.md)
- [持续集成流程](continuous-integration.md)

## Markdown 知识源

- [Markdown 知识目录规范](markdown-knowledge-spec.md)
- [Front Matter 元数据规范](front-matter-spec.md)
- [知识库配置管理](knowledge-configuration.md)
- [Markdown 文件扫描](markdown-scanning.md)
- [Markdown 内容解析](markdown-parsing.md)

## 文档同步

- [文档结构化数据模型](knowledge-document-data-model.md)
- [新增文档同步](knowledge-new-document-sync.md)
- [修改文档同步](knowledge-update-document-sync.md)
- [文档移动识别](knowledge-move-document-sync.md)
- [文档删除与恢复](knowledge-delete-restore-sync.md)
- [全量同步任务](knowledge-full-sync-task.md)
- [同步任务记录](knowledge-sync-task-record.md)
- [手动触发同步](knowledge-manual-sync.md)
- [定时同步](knowledge-scheduled-sync.md)

## 分类管理

- [分类数据模型](knowledge-category-data-model.md)
- [Markdown 文档分类同步](knowledge-category-sync.md)
- [分类查询接口](knowledge-category-query.md)
- [分类管理](knowledge-category-management.md)
- [分类删除与文档迁移](knowledge-category-delete-migration.md)

## 标签管理

- [标签数据模型](knowledge-tag-data-model.md)
- [Markdown 文档标签同步](knowledge-tag-sync.md)
- [标签查询接口](knowledge-tag-query.md)
- [标签管理](knowledge-tag-management.md)
- [标签合并](knowledge-tag-merge.md)

## 知识浏览与 API

- [文档列表接口](knowledge-document-list.md)
- [知识首页](knowledge-homepage.md)
- [分类知识列表页](category-knowledge-list.md)
- [标签知识列表页](tag-knowledge-list.md)
- [文档详情接口](knowledge-document-detail.md)

## 工程运行入口

- [项目总览](../README.md)
- [后端开发与运行](../backend/README.md)
- [数据库迁移](../backend/migrations/README.md)
- [前端开发与运行](../frontend/README.md)
- [本地基础服务](../infra/local/README.md)

## 维护规则

完成一次版本需求时，文档至少同步检查以下位置：

1. 在 `version-iteration-plan.md` 标记状态并登记交付物。
2. 新增或更新对应专题文档，并将其加入本索引。
3. 若能力、接口、迁移或运行方式发生变化，更新根 README 及对应工程 README。
4. 若实现改变既定边界或技术决策，更新架构文档或技术选型记录。
5. 校验所有本地 Markdown 链接，禁止留下失效交付物入口。
