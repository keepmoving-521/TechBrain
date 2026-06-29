# Markdown 文档分类同步说明

本文档对应 TB-V10-016：同步 Markdown 文档分类。

## 1. 同步目标

Markdown Front Matter 的 `category` 是分类归属的事实来源。同步服务将分类路径解析为分类树，自动创建缺失节点，并把文档关联到路径末级分类。

```text
category: backend/python

backend
└── python  ← knowledge_documents.category_id
```

`knowledge_documents.category` 继续保存原始规范路径，便于核对和后续回写；`category_id` 保存结构化分类外键，两者由同一次同步原子更新。

## 2. 分类路径规则

分类路径使用 `/` 分层，每一段都是分类 slug：

- 路径不能为空，不能以 `/` 开头或结尾。
- 路径总长度不超过 512 个字符。
- 每段长度不超过 80 个字符。
- 每段只允许小写英文字母、数字和中划线。
- 每段不能以中划线开头或结尾。
- 禁止空路径段和 `assets`、`drafts`、`archive` 保留目录。
- 不进行静默大小写转换，避免同一分类出现多种写法。

正确示例：

```yaml
category: backend/python
category: database/mysql
category: ai/vector-search
```

错误示例：

```yaml
category: Backend/Python
category: backend//python
category: backend/python_
category: assets/images
```

非法路径会返回 `FRONT_MATTER_INVALID_CATEGORY`，错误信息包含具体路径段和违反的规则；文档与分类均不会写入半成品数据。

## 3. 分类树建立规则

同步 `backend/python` 时按根到叶顺序处理：

1. 按 `backend` 查找根分类，不存在则创建。
2. 按 `backend/python` 查找子分类，不存在则创建并关联父分类。
3. 返回 `backend/python` 叶子节点并写入文档 `category_id`。

已存在的路径会直接复用，不重复创建分类。自动创建的分类使用：

- `name`：当前路径段 slug；后续可通过分类管理功能设置展示名称。
- `sort_order`：`0`。
- `status`：`active`。

## 4. 文档分类变更

当 Front Matter 从：

```yaml
category: backend/python
```

改为：

```yaml
category: database/mysql
```

同步服务会创建或复用 `database/mysql`，同时更新文档的 `category` 和 `category_id`。原分类不会自动删除，因为它可能仍被其他文档使用，也可能是用户希望保留的空分类。

恢复软删除文档时同样重新解析当前 Front Matter 分类，并恢复到最新分类节点。

## 5. 数据库迁移

迁移版本 `0006`：

- 为 `knowledge_documents` 增加非空 `category_id`。
- 建立到 `knowledge_categories.id` 的限制删除外键。
- 为 `category_id` 建立查询索引。
- 升级已有数据库时，根据原 `category` 字符串创建分类树并回填关联。
- 发现不符合现行规范的历史分类时中止迁移并报告具体路径，避免静默产生错误分类。

执行迁移：

```powershell
cd backend
python -m techbrain.db.migrate upgrade
```

## 6. 验收结论

TB-V10-016 已覆盖：

- 分类路径可被严格校验并正确解析为稳定树结构。
- 缺失分类自动逐级创建，已有分类稳定复用。
- 文档新增、修改和恢复时均同步分类外键。
- 文档分类变更后关联准确更新。
- 非法分类返回可定位到具体规则的错误，且不写入文档或分类数据。
