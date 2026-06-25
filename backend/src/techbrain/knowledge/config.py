"""Knowledge repository configuration loading and validation."""

from dataclasses import dataclass
from pathlib import Path

from techbrain.core.config import Settings

DEFAULT_IGNORE_PATTERNS: tuple[str, ...] = (
    ".git/",
    ".idea/",
    ".vscode/",
    "node_modules/",
    "dist/",
    "build/",
    "tmp/",
    "temp/",
    ".DS_Store",
    "Thumbs.db",
    "*.tmp",
    "*.bak",
    "*.swp",
    "~$*",
)


class KnowledgeConfigurationError(ValueError):
    """Raised when knowledge repository configuration cannot be used for sync."""


@dataclass(frozen=True)
class KnowledgeRepositoryConfig:
    """Validated knowledge repository configuration used by sync jobs."""

    root: Path
    file_encoding: str
    ignore_file_name: str
    ignore_patterns: tuple[str, ...]
    include_drafts: bool
    include_archive: bool
    sync_batch_size: int
    max_file_size_bytes: int


def build_knowledge_repository_config(settings: Settings) -> KnowledgeRepositoryConfig:
    """Validate and build sync-ready knowledge repository configuration.

    This function is intentionally strict. A sync job should call it before scanning,
    and reject execution with the returned error message if the configuration is invalid.
    """
    root = _resolve_root(settings)
    ignore_file_name = _validate_ignore_file_name(settings.knowledge_ignore_file_name)
    ignore_patterns = _load_ignore_patterns(
        root=root,
        ignore_file_name=ignore_file_name,
        encoding=settings.knowledge_file_encoding,
        extra_patterns=settings.knowledge_extra_ignore_patterns,
    )

    return KnowledgeRepositoryConfig(
        root=root,
        file_encoding=settings.knowledge_file_encoding,
        ignore_file_name=ignore_file_name,
        ignore_patterns=ignore_patterns,
        include_drafts=settings.knowledge_include_drafts,
        include_archive=settings.knowledge_include_archive,
        sync_batch_size=settings.knowledge_sync_batch_size,
        max_file_size_bytes=settings.knowledge_max_file_size_bytes,
    )


def _resolve_root(settings: Settings) -> Path:
    if settings.knowledge_root is None:
        raise KnowledgeConfigurationError("知识库根目录未配置, 请设置 TECHBRAIN_KNOWLEDGE_ROOT")

    root = settings.knowledge_root.expanduser().resolve()
    if not root.exists():
        raise KnowledgeConfigurationError(f"知识库根目录不存在: {root}")
    if not root.is_dir():
        raise KnowledgeConfigurationError(f"知识库根目录不是目录: {root}")
    return root


def _validate_ignore_file_name(ignore_file_name: str) -> str:
    candidate = ignore_file_name.strip()
    if not candidate:
        raise KnowledgeConfigurationError("知识库忽略文件名不能为空")
    if Path(candidate).name != candidate:
        raise KnowledgeConfigurationError("知识库忽略文件名不能包含路径分隔符")
    return candidate


def _load_ignore_patterns(
    *,
    root: Path,
    ignore_file_name: str,
    encoding: str,
    extra_patterns: str,
) -> tuple[str, ...]:
    patterns = [*DEFAULT_IGNORE_PATTERNS]
    ignore_file = root / ignore_file_name

    if ignore_file.exists():
        if not ignore_file.is_file():
            raise KnowledgeConfigurationError(f"知识库忽略规则不是文件: {ignore_file}")
        try:
            lines = ignore_file.read_text(encoding=encoding).splitlines()
        except UnicodeDecodeError as exc:
            raise KnowledgeConfigurationError(
                f"知识库忽略文件无法使用 {encoding} 解码: {ignore_file}"
            ) from exc

        patterns.extend(_normalize_ignore_patterns(lines))

    if extra_patterns.strip():
        patterns.extend(_normalize_ignore_patterns(extra_patterns.split(",")))

    return tuple(dict.fromkeys(patterns))


def _normalize_ignore_patterns(lines: list[str]) -> list[str]:
    patterns: list[str] = []
    for line in lines:
        pattern = line.strip()
        if not pattern or pattern.startswith("#"):
            continue
        patterns.append(pattern)
    return patterns
