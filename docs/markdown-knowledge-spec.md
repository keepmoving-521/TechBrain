# TechBrain Markdown 知识目录规范

## 1. 文档目的

本文定义 TechBrain Markdown 知识库的目录结构、文件命名、资源存放、草稿、归档和忽略规则。

该规范服务于以下目标：

- 保持 Markdown 作为唯一事实来源（SSOT）。
- 让用户脱离 TechBrain 后仍可直接阅读、编辑、迁移和 Git 管理知识。
- 为后续 Markdown 扫描、Front Matter 校验、文档同步、全文检索和 RAG 切片提供稳定输入。
- 避免不同目录、资源和临时文件混杂导致同步结果不可预测。

## 2. 基本原则

1. 一个 Markdown 文件对应一篇知识文档。
2. 知识正文和知识元数据以 Markdown 文件为准。
3. 分类目录表达主分类，一篇文档原则上只属于一个主分类。
4. 图片和附件必须位于知识根目录内，不能引用知识根目录外的本地文件。
5. 草稿和归档是知识生命周期状态，不应与正式文档混放。
6. 忽略规则必须明确、可预测，并优先保护临时文件、构建产物和私密文件。
7. 文件路径应稳定；文档身份后续以 Front Matter `id` 为准，路径移动不应改变文档身份。

## 3. 知识根目录

知识根目录是 TechBrain 扫描 Markdown 知识库的唯一入口，后续配置项建议命名为：

```text
TECHBRAIN_KNOWLEDGE_ROOT
```

示例：

```text
D:\Knowledge\TechBrain
```

知识根目录必须满足：

- 使用 UTF-8 编码保存文本文件。
- 位于用户可读写的本地目录或 Git 仓库。
- 不放在数据库、缓存、构建产物或 IDE 临时目录下。
- 路径中允许中文，但建议避免极长路径和特殊控制字符。

推荐根目录结构：

```text
TechBrain-Knowledge/
├── README.md
├── .techbrainignore
├── backend/
│   ├── python/
│   │   └── sqlalchemy-joinedload.md
│   └── mysql/
│       └── index-optimization.md
├── infrastructure/
│   ├── docker/
│   └── kubernetes/
├── ai/
│   └── rag/
├── assets/
│   ├── images/
│   └── files/
├── drafts/
│   └── ai-generated/
└── archive/
    └── 2026/
```

## 4. 顶层目录规范

| 目录 | 必选 | 是否同步为正式文档 | 用途 |
| --- | --- | --- | --- |
| `README.md` | 可选 | 否 | 知识库说明，不作为知识文档同步 |
| `.techbrainignore` | 可选 | 否 | TechBrain 扫描忽略规则 |
| 分类目录 | 必选 | 是 | 存放正式知识文档 |
| `assets/` | 可选 | 否 | 图片、附件和其他资源 |
| `drafts/` | 可选 | 否，除非后续显式开启 | 草稿、AI 生成候选内容 |
| `archive/` | 可选 | 默认不进入普通列表 | 历史归档文档 |

保留目录名：

```text
assets
drafts
archive
.git
.idea
.vscode
node_modules
dist
build
tmp
temp
```

保留目录名不得作为业务分类名使用。

## 5. 分类目录规范

分类目录用于表达稳定的主分类，建议使用 1 到 3 层层级。

正确示例：

```text
backend/python/sqlalchemy-joinedload.md
backend/mysql/index-optimization.md
infrastructure/docker/docker-compose-network.md
ai/rag/chunking-strategy.md
```

错误示例：

```text
python/backend/sqlalchemy/orm/performance/query/joinedload/note.md
```

错误原因：

- 层级过深，后续分类树难以维护。
- 目录同时表达分类、标签和具体主题，边界混乱。

分类目录命名规则：

- 使用小写英文、数字和连字符：`backend`、`python`、`rag`。
- 中文分类允许使用中文目录名，但同一知识库内应保持一致。
- 不使用空格，使用 `-` 代替。
- 不使用标点符号：`/ \ : * ? " < > | # % & { } $ ! ' @ + =`。
- 不使用临时性词语，例如 `new`、`todo`、`misc2`。

推荐分类示例：

```text
backend/
frontend/
database/
infrastructure/
ai/
architecture/
tools/
```

## 6. Markdown 文件规范

### 6.1 文件扩展名

正式支持：

```text
.md
```

暂不支持作为正式文档同步：

```text
.markdown
.mdx
.txt
.html
.docx
```

### 6.2 文件命名

推荐使用 kebab-case：

```text
sqlalchemy-joinedload.md
mysql-index-optimization.md
docker-compose-network.md
rag-chunking-strategy.md
```

命名规则：

- 文件名使用小写英文、数字和连字符。
- 文件名应表达主题，而不是日期流水。
- 不使用空格。
- 不使用 Windows 和 Unix 路径敏感字符。
- 同一目录下文件名大小写不得仅大小写不同。

允许中文文件名，但建议项目内统一一种风格。

中文文件名示例：

```text
数据库索引优化.md
SQLAlchemy-加载策略.md
```

如果使用中文文件名：

- 不混用全角和半角符号。
- 不在文件名中加入 emoji。
- 不使用过长标题作为文件名。

### 6.3 正确文件示例

```text
backend/python/sqlalchemy-joinedload.md
database/mysql/index-optimization.md
ai/rag/retrieval-evaluation.md
infrastructure/docker/compose-healthcheck.md
```

### 6.4 错误文件示例

```text
backend/python/SQLAlchemy JoinedLoad.md
backend/python/sqlalchemy_joinedload.md
backend/python/2026-06-25-1.md
backend/python/joinedload?.md
backend/python/.sqlalchemy-joinedload.md
backend/python/~$sqlalchemy-joinedload.md
```

错误原因：

- 包含空格。
- 使用下划线，不符合推荐 kebab-case。
- 文件名只有日期或流水，主题不清晰。
- 包含非法或敏感字符。
- 隐藏文件或临时文件不应作为知识文档同步。

## 7. Markdown 内容基础要求

本需求只定义目录与文件规范，Front Matter 字段将在 TB-V10-002 中单独定义。

当前阶段对正文的最低要求：

- 文件必须是 UTF-8 编码。
- 第一层标题建议与文档主题一致。
- 正文允许使用标准 Markdown：标题、列表、表格、代码块、引用、链接、图片。
- 代码块必须标注语言，便于渲染和后续索引。

正确示例：

````markdown
# SQLAlchemy joinedload 使用笔记

`joinedload` 适合在已知需要访问关联对象时减少 N+1 查询。

```python
query = select(User).options(joinedload(User.orders))
```
````

错误示例：

````markdown
# 笔记

``` 
query = select(User)
```
````

错误原因：

- 标题过于模糊。
- 代码块没有语言标识。

## 8. 图片资源规范

图片统一放在：

```text
assets/images/
```

推荐按文档或分类继续分组：

```text
assets/images/backend/python/sqlalchemy-joinedload-query-plan.png
assets/images/database/mysql/index-btree-demo.svg
```

Markdown 中使用相对路径引用：

```markdown
![joinedload 查询示意图](../../assets/images/backend/python/sqlalchemy-joinedload-query-plan.png)
```

图片规则：

- 图片必须位于知识根目录内。
- 推荐格式：`.png`、`.jpg`、`.jpeg`、`.webp`、`.svg`。
- 文件名使用小写英文、数字和连字符。
- 单张图片建议不超过 5 MB。
- 截图应去除隐私信息、密钥、内网地址和账号信息。
- 图片 alt 文本必须描述图片含义，不能写成 `image` 或空字符串。

正确示例：

```markdown
![MySQL B+Tree 索引结构](../../assets/images/database/mysql/btree-index-structure.png)
```

错误示例：

```markdown
![](C:\Users\me\Desktop\截图.png)
![image](../../../outside-secret.png)
![截图](../../assets/images/tmp/未命名 1.png)
```

错误原因：

- 使用了本机绝对路径。
- 引用了知识根目录外的文件。
- alt 文本无意义。
- 文件名包含空格和临时命名。

## 9. 附件资源规范

非图片附件统一放在：

```text
assets/files/
```

示例：

```text
assets/files/mysql/query-plan-example.json
assets/files/kubernetes/sample-deployment.yaml
```

允许的附件类型：

```text
.json
.yaml
.yml
.sql
.txt
.csv
.pdf
```

不建议放入知识库的附件：

```text
.exe
.dll
.so
.zip
.7z
.rar
.env
.key
.pem
```

如果确实需要保存压缩包或二进制文件，应通过 `.techbrainignore` 忽略，或放到外部文件管理系统中，并在 Markdown 中记录来源说明。

## 10. 草稿规范

草稿统一放在：

```text
drafts/
```

用途：

- 未完成的人工笔记。
- AI 生成但尚未审核的候选内容。
- 临时整理中的知识条目。

示例：

```text
drafts/python/sqlalchemy-loader-strategy-draft.md
drafts/ai-generated/elasticsearch-learning-route.md
```

草稿规则：

- 默认不进入正式知识列表。
- 默认不进入全文索引和 RAG 知识库。
- 可在草稿中保留不完整结构，但不得包含密钥、账号、隐私数据。
- 草稿转正时，应移动到正式分类目录，并补齐后续 Front Matter 必填字段。

正确示例：

```text
drafts/ai-generated/rag-evaluation-draft.md
```

错误示例：

```text
backend/python/draft-sqlalchemy.md
backend/python/sqlalchemy.todo.md
```

错误原因：

- 草稿混在正式分类目录中，容易被误同步。
- 用文件名表达草稿状态不稳定，后续规则难以统一。

## 11. 归档规范

归档文档统一放在：

```text
archive/
```

推荐按年份或主题组织：

```text
archive/2025/old-docker-swarm-notes.md
archive/database/mysql-5-legacy-config.md
```

归档规则：

- 归档文档仍属于知识库的一部分。
- 默认不出现在普通文档列表中。
- 可以在专门的归档视图中查询。
- 搜索是否包含归档内容由后续检索需求配置决定。
- 不建议删除有历史价值的文档，优先移动到 `archive/`。

正确示例：

```text
archive/2024/legacy-celery-config.md
```

错误示例：

```text
backend/python/old/legacy-note.md
backend/python/deprecated/legacy-note.md
```

错误原因：

- 各分类内自建 `old`、`deprecated` 会导致归档语义分散。

## 12. 忽略规则

TechBrain 支持知识根目录下的忽略文件：

```text
.techbrainignore
```

语法参考 `.gitignore` 的常用子集：

- 空行忽略。
- `#` 开头为注释。
- 支持目录忽略：`tmp/`
- 支持通配符：`*.tmp`
- 支持相对路径：`private/`
- 暂不要求支持复杂取反规则；如需恢复忽略内容，应删除对应忽略规则。

推荐 `.techbrainignore`：

```gitignore
# 系统与编辑器
.DS_Store
Thumbs.db
.idea/
.vscode/

# Git 与依赖目录
.git/
node_modules/

# 构建与缓存
dist/
build/
.cache/
tmp/
temp/

# 临时文件
*.tmp
*.bak
*.swp
~$*
*.lock

# 敏感信息
.env
.env.*
*.key
*.pem
secrets/
private/
```

默认忽略规则即使 `.techbrainignore` 不存在也应生效：

```text
.git/
.idea/
.vscode/
node_modules/
dist/
build/
tmp/
temp/
.DS_Store
Thumbs.db
*.tmp
*.bak
*.swp
~$*
```

## 13. 扫描范围规则

TechBrain 扫描时应遵守：

1. 从知识根目录开始递归扫描。
2. 只识别 `.md` 文件。
3. 跳过 `.techbrainignore` 命中的路径。
4. 跳过默认忽略路径。
5. 跳过 `assets/` 中的 Markdown 文件。
6. 跳过 `drafts/`，除非配置显式包含草稿。
7. 跳过或标记 `archive/`，默认不进入普通列表。
8. 所有解析后的真实路径必须仍位于知识根目录内，防止路径穿越。

## 14. 正确目录示例

```text
TechBrain-Knowledge/
├── README.md
├── .techbrainignore
├── backend/
│   ├── python/
│   │   ├── sqlalchemy-joinedload.md
│   │   └── fastapi-dependency-injection.md
│   └── redis/
│       └── redis-cache-pattern.md
├── database/
│   └── mysql/
│       └── index-optimization.md
├── ai/
│   └── rag/
│       └── chunking-strategy.md
├── assets/
│   ├── images/
│   │   └── database/
│   │       └── mysql-btree-index.png
│   └── files/
│       └── mysql/
│           └── explain-example.json
├── drafts/
│   └── ai-generated/
│       └── elasticsearch-learning-route.md
└── archive/
    └── 2025/
        └── old-kafka-note.md
```

为什么正确：

- 正式文档位于分类目录。
- 图片和附件位于 `assets/`。
- 草稿集中位于 `drafts/`。
- 归档集中位于 `archive/`。
- 忽略规则在 `.techbrainignore` 中声明。

## 15. 错误目录示例

```text
TechBrain-Knowledge/
├── Python Notes/
│   ├── SQLAlchemy JoinedLoad.md
│   ├── draft-fastapi.md
│   ├── old/
│   │   └── celery.md
│   └── image.png
├── 截图 1.png
├── .env
├── node_modules/
└── temp/
    └── todo.md
```

问题说明：

- `Python Notes/` 和 `SQLAlchemy JoinedLoad.md` 包含空格。
- 草稿混在正式目录。
- 归档散落在分类目录的 `old/` 下。
- 图片没有放入 `assets/images/`。
- 根目录混入截图、`.env`、依赖目录和临时目录。
- `temp/todo.md` 不应被同步。

## 16. 状态与目录关系

| 目录 | 默认状态 | 是否进入普通文档列表 | 是否进入全文索引 | 是否进入 RAG |
| --- | --- | --- | --- | --- |
| 分类目录 | 正式文档 | 是 | 是 | V2.0 起是 |
| `drafts/` | 草稿 | 否 | 否 | 否 |
| `archive/` | 归档 | 否 | 可配置 | 可配置 |
| `assets/` | 资源 | 否 | 否 | 否 |
| 忽略路径 | 忽略 | 否 | 否 | 否 |

## 17. 后续需求衔接

本规范为以下需求提供输入：

- TB-V10-002：Front Matter 元数据规范。
- TB-V10-003：知识库配置管理。
- TB-V10-004：Markdown 文件扫描。
- TB-V10-005：Markdown 内容解析。
- TB-V10-016：Markdown 文档分类同步。
- TB-V40-011：AI 草稿生成。

若未来需要调整目录规范，应提供迁移说明，并尽量保持旧知识库可被兼容扫描。

## 18. 开发检查清单

实现扫描或新增文档时必须确认：

- [ ] 文档位于知识根目录内。
- [ ] 正式文档位于分类目录，而不是 `assets/`、`drafts/` 或 `archive/`。
- [ ] 文件扩展名为 `.md`。
- [ ] 文件名符合命名规则。
- [ ] 图片位于 `assets/images/`。
- [ ] 附件位于 `assets/files/`。
- [ ] 草稿位于 `drafts/`。
- [ ] 归档位于 `archive/`。
- [ ] `.techbrainignore` 命中的内容不会被同步。
- [ ] 默认忽略目录和临时文件不会被同步。
- [ ] 所有本地资源引用解析后仍位于知识根目录内。
