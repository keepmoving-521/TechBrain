# Database migrations

TechBrain 使用 Alembic 管理数据库结构版本。

常用命令：

```powershell
python -m techbrain.db.migrate upgrade head
python -m techbrain.db.migrate current
python -m techbrain.db.migrate history
```

V0.1 只建立迁移机制与基线版本，业务表会在后续需求中逐步加入。
