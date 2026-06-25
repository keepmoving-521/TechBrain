"""Markdown document parser for TechBrain knowledge files."""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal
from urllib.parse import urlparse

from techbrain.knowledge.scanner import MarkdownFile

SUPPORTED_SCHEMA_VERSION = 1
VALID_STATUSES = {"published", "draft", "archived", "deprecated"}
VALID_SOURCE_TYPES = {"original", "excerpt", "translation", "summary", "ai_generated", "imported"}
VALID_VISIBILITIES = {"private", "shared"}
RESERVED_CATEGORY_PARTS = {"assets", "drafts", "archive"}

HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
FENCED_CODE_PATTERN = re.compile(r"^(```|~~~)\s*([^\s`]*)?.*$")
INLINE_LINK_PATTERN = re.compile(r"(?<!!)\[([^\]]+)]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{1,118}[a-z0-9]$")


@dataclass(frozen=True)
class FrontMatterSource:
    """Source metadata parsed from Front Matter."""

    type: str
    url: str | None
    title: str | None
    author: str | None
    retrieved_at: datetime | None
    note: str | None


@dataclass(frozen=True)
class FrontMatter:
    """Validated Front Matter metadata."""

    schema_version: int
    id: str
    title: str
    category: str
    tags: tuple[str, ...]
    status: str
    created_at: datetime
    updated_at: datetime
    summary: str | None
    source: FrontMatterSource
    aliases: tuple[str, ...]
    language: str
    visibility: str


@dataclass(frozen=True)
class MarkdownHeading:
    """Markdown heading structure."""

    level: int
    text: str
    line: int


@dataclass(frozen=True)
class MarkdownCodeBlock:
    """Markdown fenced code block."""

    language: str | None
    start_line: int
    end_line: int
    code: str


@dataclass(frozen=True)
class MarkdownLink:
    """Markdown inline link."""

    text: str
    target: str
    line: int


@dataclass(frozen=True)
class MarkdownParseIssue:
    """A parser error or warning with file and position context."""

    file_path: str
    code: str
    message: str
    line: int | None = None
    column: int | None = None
    field: str | None = None


@dataclass(frozen=True)
class ParsedMarkdownDocument:
    """A successfully parsed Markdown document."""

    file: MarkdownFile
    front_matter: FrontMatter
    body: str
    headings: tuple[MarkdownHeading, ...]
    code_blocks: tuple[MarkdownCodeBlock, ...]
    links: tuple[MarkdownLink, ...]
    warnings: tuple[MarkdownParseIssue, ...] = ()


@dataclass(frozen=True)
class MarkdownParseResult:
    """Markdown parse result."""

    status: Literal["valid", "error"]
    document: ParsedMarkdownDocument | None
    errors: tuple[MarkdownParseIssue, ...]


def parse_markdown_file(
    markdown_file: MarkdownFile,
    *,
    encoding: str = "utf-8",
) -> MarkdownParseResult:
    """Read and parse one Markdown file."""
    try:
        content = markdown_file.path.read_text(encoding=encoding)
    except UnicodeDecodeError as exc:
        return _error_result(
            markdown_file,
            "MARKDOWN_DECODE_ERROR",
            f"Markdown 文件无法使用 {encoding} 解码: {exc}",
        )
    except OSError as exc:
        return _error_result(
            markdown_file,
            "MARKDOWN_READ_ERROR",
            f"Markdown 文件读取失败: {exc}",
        )

    return parse_markdown_content(markdown_file, content)


def parse_markdown_content(markdown_file: MarkdownFile, content: str) -> MarkdownParseResult:
    """Parse Markdown content into unified metadata and structure."""
    front_matter_result = _split_front_matter(markdown_file, content)
    if isinstance(front_matter_result, MarkdownParseResult):
        return front_matter_result

    raw_front_matter, body, front_matter_start_line = front_matter_result
    yaml_result = _parse_front_matter_yaml(markdown_file, raw_front_matter, front_matter_start_line)
    if isinstance(yaml_result, MarkdownParseResult):
        return yaml_result

    front_matter, errors = _validate_front_matter(markdown_file, yaml_result)
    if errors:
        return MarkdownParseResult(status="error", document=None, errors=tuple(errors))

    body_start_line = front_matter_start_line + raw_front_matter.count("\n") + 2
    document = ParsedMarkdownDocument(
        file=markdown_file,
        front_matter=front_matter,
        body=body,
        headings=_extract_headings(body, body_start_line),
        code_blocks=_extract_code_blocks(
            body,
            body_start_line,
        ),
        links=_extract_links(body, body_start_line),
    )
    return MarkdownParseResult(status="valid", document=document, errors=())


def _split_front_matter(
    markdown_file: MarkdownFile,
    content: str,
) -> tuple[str, str, int] | MarkdownParseResult:
    lines = content.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return _error_result(
            markdown_file,
            "FRONT_MATTER_MISSING",
            "Front Matter 必须位于文件顶部并以 --- 开始",
            line=1,
            column=1,
        )

    for index, line in enumerate(lines[1:], start=2):
        if line.strip() == "---":
            raw_front_matter = "".join(lines[1 : index - 1])
            body = "".join(lines[index:])
            return raw_front_matter, body, 2

    return _error_result(
        markdown_file,
        "FRONT_MATTER_NOT_CLOSED",
        "Front Matter 缺少结束 ---",
        line=1,
        column=1,
    )


def _parse_front_matter_yaml(
    markdown_file: MarkdownFile,
    raw_front_matter: str,
    start_line: int,
) -> dict[str, Any] | MarkdownParseResult:
    data: dict[str, Any] = {}
    lines = raw_front_matter.splitlines()
    index = 0

    while index < len(lines):
        raw_line = lines[index]
        line_number = start_line + index
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            index += 1
            continue
        if raw_line.startswith(" "):
            return _yaml_error(markdown_file, "YAML_UNEXPECTED_INDENT", line_number)
        if ":" not in raw_line:
            return _yaml_error(markdown_file, "YAML_INVALID_LINE", line_number)

        key, raw_value = raw_line.split(":", maxsplit=1)
        key = key.strip()
        value = raw_value.strip()
        if not key:
            return _yaml_error(markdown_file, "YAML_EMPTY_KEY", line_number)

        if value:
            data[key] = _parse_scalar(value)
            index += 1
            continue

        nested_lines: list[str] = []
        index += 1
        while index < len(lines):
            nested_line = lines[index]
            if nested_line.strip() and not nested_line.startswith(" "):
                break
            nested_lines.append(nested_line)
            index += 1

        data[key] = _parse_nested_yaml_value(markdown_file, key, nested_lines, line_number)
        if isinstance(data[key], MarkdownParseResult):
            return data[key]

    return data


def _parse_nested_yaml_value(
    markdown_file: MarkdownFile,
    key: str,
    nested_lines: list[str],
    line_number: int,
) -> Any:
    meaningful_lines = [line for line in nested_lines if line.strip()]
    if not meaningful_lines:
        return None

    if all(line.startswith("  - ") for line in meaningful_lines):
        return [_parse_scalar(line[4:].strip()) for line in meaningful_lines]

    nested_object: dict[str, Any] = {}
    for offset, line in enumerate(nested_lines, start=1):
        if not line.strip():
            continue
        if not line.startswith("  ") or line.startswith("    "):
            return _yaml_error(markdown_file, "YAML_UNSUPPORTED_NESTING", line_number + offset)
        nested = line[2:]
        if ":" not in nested:
            return _yaml_error(markdown_file, "YAML_INVALID_LINE", line_number + offset)
        nested_key, raw_value = nested.split(":", maxsplit=1)
        nested_object[nested_key.strip()] = _parse_scalar(raw_value.strip())

    if not nested_object:
        return _yaml_error(
            markdown_file,
            "YAML_EMPTY_VALUE",
            line_number,
            f"字段 {key} 缺少值",
        )
    return nested_object


def _parse_scalar(value: str) -> Any:
    if value in {"null", "Null", "NULL", "~"}:
        return None
    if value == "[]":
        return []
    if value == "{}":
        return {}
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def _validate_front_matter(
    markdown_file: MarkdownFile,
    data: dict[str, Any],
) -> tuple[FrontMatter, list[MarkdownParseIssue]]:
    errors: list[MarkdownParseIssue] = []

    schema_version = _require_int(markdown_file, data, "schema_version", errors)
    document_id = _require_string(markdown_file, data, "id", errors)
    title = _require_string(markdown_file, data, "title", errors)
    category = _require_string(markdown_file, data, "category", errors)
    created_at = _require_datetime(markdown_file, data, "created_at", errors)
    updated_at = _require_datetime(markdown_file, data, "updated_at", errors)

    if schema_version is not None and schema_version != SUPPORTED_SCHEMA_VERSION:
        errors.append(
            _field_error(markdown_file, "FRONT_MATTER_UNSUPPORTED_SCHEMA", "schema_version")
        )
    if document_id is not None and not ID_PATTERN.fullmatch(document_id):
        errors.append(_field_error(markdown_file, "FRONT_MATTER_INVALID_ID", "id"))
    if title is not None and (not title.strip() or title.strip().startswith("#")):
        errors.append(_field_error(markdown_file, "FRONT_MATTER_INVALID_TITLE", "title"))
    if category is not None and not _is_valid_category(category):
        errors.append(_field_error(markdown_file, "FRONT_MATTER_INVALID_CATEGORY", "category"))
    if created_at is not None and updated_at is not None and updated_at < created_at:
        errors.append(
            _field_error(
                markdown_file,
                "FRONT_MATTER_INVALID_TIME_ORDER",
                "updated_at",
                "updated_at 不得早于 created_at",
            )
        )

    tags = _optional_string_list(markdown_file, data, "tags", errors)
    status = _optional_enum(markdown_file, data, "status", VALID_STATUSES, "published", errors)
    summary = _optional_string(markdown_file, data, "summary", errors)
    source = _optional_source(markdown_file, data, errors)
    aliases = _optional_string_list(markdown_file, data, "aliases", errors)
    language = _optional_string(markdown_file, data, "language", errors) or "zh-CN"
    visibility = _optional_enum(
        markdown_file,
        data,
        "visibility",
        VALID_VISIBILITIES,
        "private",
        errors,
    )

    if errors:
        return _empty_front_matter(), errors

    return (
        FrontMatter(
            schema_version=schema_version or SUPPORTED_SCHEMA_VERSION,
            id=document_id or "",
            title=title.strip() if title else "",
            category=category or "",
            tags=tuple(tags),
            status=status,
            created_at=created_at or datetime.min,
            updated_at=updated_at or datetime.min,
            summary=summary,
            source=source,
            aliases=tuple(aliases),
            language=language,
            visibility=visibility,
        ),
        [],
    )


def _require_int(
    markdown_file: MarkdownFile,
    data: dict[str, Any],
    field: str,
    errors: list[MarkdownParseIssue],
) -> int | None:
    value = data.get(field)
    if field not in data:
        errors.append(_field_error(markdown_file, "FRONT_MATTER_REQUIRED_FIELD_MISSING", field))
        return None
    if not isinstance(value, int):
        errors.append(_field_error(markdown_file, "FRONT_MATTER_INVALID_FIELD_TYPE", field))
        return None
    return value


def _require_string(
    markdown_file: MarkdownFile,
    data: dict[str, Any],
    field: str,
    errors: list[MarkdownParseIssue],
) -> str | None:
    value = data.get(field)
    if field not in data:
        errors.append(_field_error(markdown_file, "FRONT_MATTER_REQUIRED_FIELD_MISSING", field))
        return None
    if not isinstance(value, str):
        errors.append(_field_error(markdown_file, "FRONT_MATTER_INVALID_FIELD_TYPE", field))
        return None
    return value.strip()


def _require_datetime(
    markdown_file: MarkdownFile,
    data: dict[str, Any],
    field: str,
    errors: list[MarkdownParseIssue],
) -> datetime | None:
    value = _require_string(markdown_file, data, field, errors)
    if value is None:
        return None
    parsed = _parse_datetime(value)
    if parsed is None:
        errors.append(_field_error(markdown_file, "FRONT_MATTER_INVALID_DATETIME", field))
    return parsed


def _optional_string_list(
    markdown_file: MarkdownFile,
    data: dict[str, Any],
    field: str,
    errors: list[MarkdownParseIssue],
) -> list[str]:
    if field not in data or data[field] is None:
        return []
    value = data[field]
    if not isinstance(value, list):
        errors.append(_field_error(markdown_file, "FRONT_MATTER_INVALID_FIELD_TYPE", field))
        return []

    items: list[str] = []
    lowered_items: set[str] = set()
    for item in value:
        if not isinstance(item, str) or not item.strip():
            errors.append(_field_error(markdown_file, "FRONT_MATTER_INVALID_LIST_ITEM", field))
            continue
        normalized = item.strip()
        lowered = normalized.lower()
        if lowered in lowered_items:
            errors.append(_field_error(markdown_file, "FRONT_MATTER_DUPLICATE_LIST_ITEM", field))
            continue
        lowered_items.add(lowered)
        items.append(normalized)
    return items


def _optional_enum(
    markdown_file: MarkdownFile,
    data: dict[str, Any],
    field: str,
    values: set[str],
    default: str,
    errors: list[MarkdownParseIssue],
) -> str:
    if field not in data or data[field] is None:
        return default
    value = data[field]
    if not isinstance(value, str) or value not in values:
        errors.append(_field_error(markdown_file, "FRONT_MATTER_INVALID_ENUM", field))
        return default
    return value


def _optional_string(
    markdown_file: MarkdownFile,
    data: dict[str, Any],
    field: str,
    errors: list[MarkdownParseIssue],
) -> str | None:
    if field not in data or data[field] is None:
        return None
    value = data[field]
    if not isinstance(value, str):
        errors.append(_field_error(markdown_file, "FRONT_MATTER_INVALID_FIELD_TYPE", field))
        return None
    return value.strip()


def _optional_source(
    markdown_file: MarkdownFile,
    data: dict[str, Any],
    errors: list[MarkdownParseIssue],
) -> FrontMatterSource:
    value = data.get("source", {"type": "original"})
    if value is None:
        value = {"type": "original"}
    if not isinstance(value, dict):
        errors.append(_field_error(markdown_file, "FRONT_MATTER_INVALID_FIELD_TYPE", "source"))
        return _default_source()

    source_type = value.get("type")
    if not isinstance(source_type, str) or source_type not in VALID_SOURCE_TYPES:
        errors.append(_field_error(markdown_file, "FRONT_MATTER_INVALID_ENUM", "source.type"))
        source_type = "original"

    source_url = value.get("url")
    if source_url is not None and (
        not isinstance(source_url, str) or urlparse(source_url).scheme not in {"http", "https"}
    ):
        errors.append(_field_error(markdown_file, "FRONT_MATTER_INVALID_URL", "source.url"))
        source_url = None

    retrieved_at = value.get("retrieved_at")
    parsed_retrieved_at = None
    if retrieved_at is not None:
        if not isinstance(retrieved_at, str):
            errors.append(
                _field_error(markdown_file, "FRONT_MATTER_INVALID_DATETIME", "source.retrieved_at")
            )
        else:
            parsed_retrieved_at = _parse_datetime(retrieved_at)
            if parsed_retrieved_at is None:
                errors.append(
                    _field_error(
                        markdown_file,
                        "FRONT_MATTER_INVALID_DATETIME",
                        "source.retrieved_at",
                    )
                )

    return FrontMatterSource(
        type=source_type,
        url=source_url,
        title=_dict_string(value, "title"),
        author=_dict_string(value, "author"),
        retrieved_at=parsed_retrieved_at,
        note=_dict_string(value, "note"),
    )


def _dict_string(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)
    return value.strip() if isinstance(value, str) else None


def _parse_datetime(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed


def _is_valid_category(category: str) -> bool:
    if not category or category.startswith("/") or category.endswith("/") or ".." in category:
        return False
    parts = category.split("/")
    return all(part and part not in RESERVED_CATEGORY_PARTS for part in parts)


def _extract_headings(body: str, body_start_line: int) -> tuple[MarkdownHeading, ...]:
    headings: list[MarkdownHeading] = []
    in_code_block = False

    for offset, line in enumerate(body.splitlines(), start=0):
        if FENCED_CODE_PATTERN.match(line):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        match = HEADING_PATTERN.match(line)
        if match:
            headings.append(
                MarkdownHeading(
                    level=len(match.group(1)),
                    text=match.group(2).strip(),
                    line=body_start_line + offset,
                )
            )
    return tuple(headings)


def _extract_code_blocks(body: str, body_start_line: int) -> tuple[MarkdownCodeBlock, ...]:
    code_blocks: list[MarkdownCodeBlock] = []
    fence: str | None = None
    language: str | None = None
    start_line = 0
    code_lines: list[str] = []

    for offset, line in enumerate(body.splitlines(), start=0):
        match = FENCED_CODE_PATTERN.match(line)
        if match and fence is None:
            fence = match.group(1)
            language = match.group(2) or None
            start_line = body_start_line + offset
            code_lines = []
            continue
        if fence is not None and line.startswith(fence):
            code_blocks.append(
                MarkdownCodeBlock(
                    language=language,
                    start_line=start_line,
                    end_line=body_start_line + offset,
                    code="\n".join(code_lines),
                )
            )
            fence = None
            language = None
            code_lines = []
            continue
        if fence is not None:
            code_lines.append(line)

    return tuple(code_blocks)


def _extract_links(body: str, body_start_line: int) -> tuple[MarkdownLink, ...]:
    links: list[MarkdownLink] = []
    in_code_block = False

    for offset, line in enumerate(body.splitlines(), start=0):
        if FENCED_CODE_PATTERN.match(line):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        for match in INLINE_LINK_PATTERN.finditer(line):
            links.append(
                MarkdownLink(
                    text=match.group(1),
                    target=match.group(2),
                    line=body_start_line + offset,
                )
            )
    return tuple(links)


def _field_error(
    markdown_file: MarkdownFile,
    code: str,
    field: str,
    message: str | None = None,
) -> MarkdownParseIssue:
    return MarkdownParseIssue(
        file_path=markdown_file.relative_path,
        code=code,
        message=message or f"Front Matter 字段 {field} 不符合规范",
        field=field,
    )


def _yaml_error(
    markdown_file: MarkdownFile,
    code: str,
    line: int,
    message: str = "Front Matter YAML 格式错误",
) -> MarkdownParseResult:
    return _error_result(markdown_file, code, message, line=line, column=1)


def _error_result(
    markdown_file: MarkdownFile,
    code: str,
    message: str,
    *,
    line: int | None = None,
    column: int | None = None,
) -> MarkdownParseResult:
    return MarkdownParseResult(
        status="error",
        document=None,
        errors=(
            MarkdownParseIssue(
                file_path=markdown_file.relative_path,
                code=code,
                message=message,
                line=line,
                column=column,
            ),
        ),
    )


def _default_source() -> FrontMatterSource:
    return FrontMatterSource(
        type="original",
        url=None,
        title=None,
        author=None,
        retrieved_at=None,
        note=None,
    )


def _empty_front_matter() -> FrontMatter:
    return FrontMatter(
        schema_version=SUPPORTED_SCHEMA_VERSION,
        id="",
        title="",
        category="",
        tags=(),
        status="published",
        created_at=datetime.min,
        updated_at=datetime.min,
        summary=None,
        source=_default_source(),
        aliases=(),
        language="zh-CN",
        visibility="private",
    )
