# Database migrations

TechBrain 使用 Alembic 管理数据库结构版本。

常用命令：

```powershell
python -m techbrain.db.migrate upgrade head
python -m techbrain.db.migrate current
python -m techbrain.db.migrate history
```

## 当前迁移

| 版本 | 内容 |
| --- | --- |
| `0001` | 建立 Alembic 迁移基线 |
| `0002` | 创建 `knowledge_documents` 文档表 |
| `0003` | 增加 Markdown 正文字段 |
| `0004` | 创建同步任务及失败记录表 |
| `0005` | 创建层级分类表 |
| `0006` | 建立文档与分类外键关联 |
| `0007` | 创建标签及文档标签关联表 |

空数据库执行 `upgrade head` 后会一次性建立当前 V1.0 已实现能力所需的全部结构。新增或修改业务模型时，必须同步增加版本化迁移，不使用运行时自动建表替代正式迁移。
