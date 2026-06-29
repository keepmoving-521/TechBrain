# 分类管理说明

本文档对应 TB-V10-018：实现分类管理。

## 1. 能力范围

分类管理提供：

- 新建空分类。
- 修改分类展示名称。
- 修改分类 slug。
- 移动分类到根级或其他父分类。
- 修改同级排序值。
- 分类路径变化时，递归更新后代路径并安全回写 Markdown 元数据。

分类删除与删除前的文档迁移由 TB-V10-019 实现，详见[分类删除与文档迁移说明](knowledge-category-delete-migration.md)。

## 2. API

### 2.1 新建分类

```http
POST /api/v1/categories
Content-Type: application/json
```

```json
{
  "name": "Python",
  "slug": "python",
  "parent_id": 1,
  "sort_order": 10
}
```

字段规则：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `name` | 是 | 展示名称，最大 80 个字符 |
| `slug` | 是 | 路径片段，只允许字母、数字和中划线 |
| `parent_id` | 否 | 父分类 ID，`null` 表示根分类 |
| `sort_order` | 否 | 非负整数，默认 `0` |

新建成功返回 `201 Created` 和分类详情。新建分类没有 Markdown 文档，因此不创建目录或占位文件。

### 2.2 重命名、移动和排序

```http
PATCH /api/v1/categories/{category_id}
Content-Type: application/json
```

```json
{
  "name": "Python Engineering",
  "slug": "python-engineering",
  "parent_id": 3,
  "sort_order": 20
}
```

所有字段均可选，但请求至少包含一个字段：

- `name`：只改变平台展示名称，不改变 Markdown 分类路径。
- `slug`：改变当前分类路径，并递归改变所有后代路径。
- `parent_id`：移动分类；传 `null` 表示移动到根级。
- `sort_order`：改变当前分类在同级中的排序。

成功返回更新后的分类详情。

## 3. Markdown SSOT 一致性策略

Markdown Front Matter 仍是文档知识元数据的唯一事实来源。

当 `slug` 或 `parent_id` 导致分类路径变化时，系统按以下顺序执行：

1. 计算当前分类及所有后代分类的新路径。
2. 检查目标路径是否与分类树中其他节点冲突。
3. 加载所有受影响文档，确认源文件存在且仍位于配置的知识库内。
4. 重新解析 Markdown，比较文档 ID、分类、正文哈希和 Front Matter 语义哈希。
5. 任何文件在最近同步后发生外部修改时，整体拒绝操作。
6. 将受影响文档的 `category` 和 `updated_at` 原子回写到 Front Matter。
7. 重新执行文档同步，更新数据库分类路径、分类关联及 Front Matter 哈希。
8. 所有文件和数据库更新成功后提交事务。

示例：

```text
backend/python
└── sqlalchemy
```

把 `python` 移动到 `database` 并改为 `py` 后：

```text
database/py
└── sqlalchemy
```

对应 Markdown 自动更新：

```yaml
category: database/py
```

后代文档更新为：

```yaml
category: database/py/sqlalchemy
```

## 4. 文件位置策略

分类管理只修改 Front Matter 分类元数据，不自动移动物理 Markdown 文件。

这是当前版本的明确策略，原因是移动文件可能破坏：

- Markdown 相对链接。
- 图片和附件引用。
- 外部编辑器书签。
- Git 历史中的路径跟踪。

分类归属查询和同步以 Front Matter `category` 为准。若希望目录路径与分类路径保持完全一致，应由用户在 Git 或编辑器中显式移动文件，再执行同步。后续可以增加带链接修复和移动预览的独立文件整理功能。

## 5. 冲突与回滚

以下情况返回 `409 Conflict`，不会静默覆盖：

- 新建或移动后的分类路径已存在。
- 将分类移动到自身或自己的后代下。
- 分类或后代包含源文件已删除的文档。
- Markdown 文件在最近同步后发生变化。
- Markdown 文件在校验完成后、实际写入前再次变化。
- Front Matter 缺少必要回写字段或包含重复字段。
- 文件读取、写入或重新同步失败。
- 同步任务或其他分类写操作正在执行。

多文档回写采用批量补偿机制。若中途某个文件写入失败：

- 数据库事务回滚。
- 已写入文件按相反顺序恢复原始内容。
- 未写入文件保持不变。
- 如果文件又被外部修改导致无法安全恢复，错误信息会列出需要人工检查的文件。

## 6. 状态码

| 状态码 | 场景 |
| --- | --- |
| `200` | 分类修改成功 |
| `201` | 分类创建成功 |
| `400` | 分类名称、slug、路径长度或请求语义不合法 |
| `404` | 分类或目标父分类不存在 |
| `409` | 路径、层级、文件版本或运行任务冲突 |
| `422` | 请求字段类型错误或不允许的 `null` 值 |

错误响应遵循 TechBrain API 统一错误格式。

## 7. 验收结论

TB-V10-018 已覆盖：

- 支持分类新建、展示名称修改、slug 修改、移动和排序。
- 路径变更递归更新全部后代分类。
- 受影响文档分类元数据安全回写 Markdown。
- 外部修改、目标路径和循环层级冲突均明确拒绝。
- 数据库和多文件写入失败时执行事务回滚与文件补偿。
- 分类管理与知识同步使用同一运行锁，避免并发写入冲突。
