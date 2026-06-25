"""Markdown knowledge parser tests."""

from pathlib import Path

from techbrain.knowledge.parser import parse_markdown_content, parse_markdown_file
from techbrain.knowledge.scanner import MarkdownFile


def _markdown_file(relative_path: str = "backend/python/sqlalchemy-joinedload.md") -> MarkdownFile:
    path = Path(".pytest_tmp") / relative_path
    return MarkdownFile(path=path.resolve(), relative_path=relative_path, size_bytes=0)


def test_parse_markdown_content_returns_unified_document_structure() -> None:
    content = """---
schema_version: 1
id: sqlalchemy-joinedload
title: SQLAlchemy joinedload 使用指南
category: backend/python
tags:
  - orm
  - sqlalchemy
status: published
created_at: 2026-06-25T10:00:00+08:00
updated_at: 2026-06-25T10:30:00+08:00
summary: SQLAlchemy joinedload 的实践说明。
source:
  type: summary
  url: https://docs.sqlalchemy.org/
  title: SQLAlchemy Documentation
  retrieved_at: 2026-06-25T10:00:00+08:00
aliases:
  - joinedload
language: zh-CN
visibility: private
---

# SQLAlchemy joinedload 使用指南

参考 [SQLAlchemy 文档](https://docs.sqlalchemy.org/)。

## 示例

```python
query = select(User)
# [not a link](https://example.com)
```
"""

    result = parse_markdown_content(_markdown_file(), content)

    assert result.status == "valid"
    assert result.errors == ()
    assert result.document is not None
    assert result.document.front_matter.id == "sqlalchemy-joinedload"
    assert result.document.front_matter.tags == ("orm", "sqlalchemy")
    assert result.document.front_matter.source.type == "summary"
    assert result.document.front_matter.source.url == "https://docs.sqlalchemy.org/"
    assert [heading.text for heading in result.document.headings] == [
        "SQLAlchemy joinedload 使用指南",
        "示例",
    ]
    assert result.document.code_blocks[0].language == "python"
    assert "select(User)" in result.document.code_blocks[0].code
    assert [(link.text, link.target) for link in result.document.links] == [
        ("SQLAlchemy 文档", "https://docs.sqlalchemy.org/")
    ]


def test_parse_markdown_content_rejects_missing_front_matter_at_top() -> None:
    content = """# Title

---
schema_version: 1
---
"""

    result = parse_markdown_content(_markdown_file(), content)

    assert result.status == "error"
    assert result.errors[0].code == "FRONT_MATTER_MISSING"
    assert result.errors[0].line == 1
    assert result.errors[0].file_path == "backend/python/sqlalchemy-joinedload.md"


def test_parse_markdown_content_rejects_unclosed_front_matter() -> None:
    content = """---
schema_version: 1
id: sqlalchemy-joinedload
"""

    result = parse_markdown_content(_markdown_file(), content)

    assert result.status == "error"
    assert result.errors[0].code == "FRONT_MATTER_NOT_CLOSED"


def test_parse_markdown_content_rejects_yaml_format_error_with_line() -> None:
    content = """---
schema_version: 1
  id: sqlalchemy-joinedload
---

# Title
"""

    result = parse_markdown_content(_markdown_file(), content)

    assert result.status == "error"
    assert result.errors[0].code == "YAML_UNEXPECTED_INDENT"
    assert result.errors[0].line == 3


def test_parse_markdown_content_reports_required_field_errors() -> None:
    content = """---
schema_version: 1
title: SQLAlchemy joinedload 使用指南
category: backend/python
created_at: 2026-06-25T10:00:00+08:00
updated_at: 2026-06-25T10:30:00+08:00
---

# SQLAlchemy joinedload 使用指南
"""

    result = parse_markdown_content(_markdown_file(), content)

    assert result.status == "error"
    assert any(error.field == "id" for error in result.errors)
    assert any(error.code == "FRONT_MATTER_REQUIRED_FIELD_MISSING" for error in result.errors)


def test_parse_markdown_content_reports_invalid_datetime_order() -> None:
    content = """---
schema_version: 1
id: sqlalchemy-joinedload
title: SQLAlchemy joinedload 使用指南
category: backend/python
created_at: 2026-06-25T10:00:00+08:00
updated_at: 2026-06-24T10:00:00+08:00
---

# SQLAlchemy joinedload 使用指南
"""

    result = parse_markdown_content(_markdown_file(), content)

    assert result.status == "error"
    assert result.errors[0].code == "FRONT_MATTER_INVALID_TIME_ORDER"
    assert result.errors[0].field == "updated_at"


def test_parse_markdown_content_reports_invalid_optional_fields() -> None:
    content = """---
schema_version: 1
id: sqlalchemy-joinedload
title: SQLAlchemy joinedload 使用指南
category: backend/python
tags:
  - orm
  - ORM
status: done
created_at: 2026-06-25T10:00:00+08:00
updated_at: 2026-06-25T10:30:00+08:00
source:
  type: imported
  url: file:///tmp/source.md
visibility: public
---

# SQLAlchemy joinedload 使用指南
"""

    result = parse_markdown_content(_markdown_file(), content)

    assert result.status == "error"
    assert {error.field for error in result.errors} >= {
        "tags",
        "status",
        "source.url",
        "visibility",
    }


def test_parse_markdown_file_reports_decode_error() -> None:
    path = Path(".pytest_tmp") / "parser_bad_encoding.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\xff\xfe\x00")
    markdown_file = MarkdownFile(
        path=path,
        relative_path="backend/python/bad.md",
        size_bytes=path.stat().st_size,
    )

    result = parse_markdown_file(markdown_file, encoding="utf-8")

    assert result.status == "error"
    assert result.errors[0].code == "MARKDOWN_DECODE_ERROR"


def test_parse_markdown_file_reports_read_error() -> None:
    markdown_file = MarkdownFile(
        path=Path(".pytest_tmp") / "missing.md",
        relative_path="backend/python/missing.md",
        size_bytes=0,
    )

    result = parse_markdown_file(markdown_file, encoding="utf-8")

    assert result.status == "error"
    assert result.errors[0].code == "MARKDOWN_READ_ERROR"


def test_parse_markdown_content_reports_invalid_required_field_values() -> None:
    content = """---
schema_version: 2
id: SQLAlchemy JoinedLoad
title: "# SQLAlchemy joinedload 使用指南"
category: /backend/python/
created_at: 2026-06-25
updated_at: 2026-06-25T10:30:00+08:00
summary: []
source: imported
aliases: alias
---

# SQLAlchemy joinedload 使用指南
"""

    result = parse_markdown_content(_markdown_file(), content)

    assert result.status == "error"
    assert {error.field for error in result.errors} >= {
        "schema_version",
        "id",
        "title",
        "category",
        "created_at",
        "summary",
        "source",
        "aliases",
    }


def test_parse_markdown_content_reports_invalid_source_retrieved_at() -> None:
    content = """---
schema_version: 1
id: sqlalchemy-joinedload
title: SQLAlchemy joinedload 使用指南
category: backend/python
created_at: 2026-06-25T10:00:00+08:00
updated_at: 2026-06-25T10:30:00+08:00
source:
  type: summary
  retrieved_at: 2026-06-25
---

# SQLAlchemy joinedload 使用指南
"""

    result = parse_markdown_content(_markdown_file(), content)

    assert result.status == "error"
    assert result.errors[0].field == "source.retrieved_at"
    assert result.errors[0].code == "FRONT_MATTER_INVALID_DATETIME"


def test_parse_markdown_content_reports_invalid_yaml_lines() -> None:
    content = """---
schema_version: 1
id
---
"""

    result = parse_markdown_content(_markdown_file(), content)

    assert result.status == "error"
    assert result.errors[0].code == "YAML_INVALID_LINE"


def test_parse_markdown_content_reports_invalid_nested_yaml() -> None:
    content = """---
schema_version: 1
id: sqlalchemy-joinedload
source:
    type: original
---
"""

    result = parse_markdown_content(_markdown_file(), content)

    assert result.status == "error"
    assert result.errors[0].code == "YAML_UNSUPPORTED_NESTING"
