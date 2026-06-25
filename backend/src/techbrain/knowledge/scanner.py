"""Markdown knowledge repository scanner."""

import fnmatch
import os
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from techbrain.knowledge.config import KnowledgeRepositoryConfig

MARKDOWN_SUFFIX = ".md"
ROOT_README_FILE_NAME = "README.md"
ASSETS_DIR_NAME = "assets"
DRAFTS_DIR_NAME = "drafts"
ARCHIVE_DIR_NAME = "archive"


@dataclass(frozen=True)
class MarkdownFile:
    """A Markdown file discovered in the knowledge repository."""

    path: Path
    relative_path: str
    size_bytes: int


@dataclass(frozen=True)
class MarkdownScanError:
    """A non-fatal path error found while scanning the knowledge repository."""

    path: Path
    code: str
    message: str


@dataclass(frozen=True)
class MarkdownScanResult:
    """Markdown scan output."""

    files: tuple[MarkdownFile, ...]
    errors: tuple[MarkdownScanError, ...]


def scan_markdown_files(config: KnowledgeRepositoryConfig) -> MarkdownScanResult:
    """Recursively scan a knowledge repository for syncable Markdown files."""
    files: list[MarkdownFile] = []
    errors: list[MarkdownScanError] = []

    _scan_directory(config.root, config=config, files=files, errors=errors)

    return MarkdownScanResult(
        files=tuple(sorted(files, key=lambda file: file.relative_path)),
        errors=tuple(errors),
    )


def _scan_directory(
    directory: Path,
    *,
    config: KnowledgeRepositoryConfig,
    files: list[MarkdownFile],
    errors: list[MarkdownScanError],
) -> None:
    try:
        with os.scandir(directory) as entries:
            for entry in entries:
                entry_path = Path(entry.path)
                try:
                    if entry.is_dir(follow_symlinks=False):
                        if _should_skip_path(entry_path, is_dir=True, config=config):
                            continue
                        _scan_directory(entry_path, config=config, files=files, errors=errors)
                        continue

                    if not entry.is_file(follow_symlinks=False):
                        continue

                    if _should_skip_path(entry_path, is_dir=False, config=config):
                        continue
                    if entry_path.suffix.lower() != MARKDOWN_SUFFIX:
                        continue

                    _append_markdown_file(entry_path, config=config, files=files, errors=errors)
                except OSError as exc:
                    errors.append(_path_error(entry_path, "PATH_ACCESS_ERROR", exc))
    except OSError as exc:
        errors.append(_path_error(directory, "DIRECTORY_ACCESS_ERROR", exc))


def _append_markdown_file(
    path: Path,
    *,
    config: KnowledgeRepositoryConfig,
    files: list[MarkdownFile],
    errors: list[MarkdownScanError],
) -> None:
    try:
        resolved_path = path.resolve(strict=True)
    except OSError as exc:
        errors.append(_path_error(path, "PATH_RESOLVE_ERROR", exc))
        return

    if not _is_relative_to(resolved_path, config.root):
        errors.append(
            MarkdownScanError(
                path=path,
                code="PATH_OUTSIDE_ROOT",
                message="解析后的真实路径不在知识库根目录内",
            )
        )
        return

    try:
        stat_result = path.stat()
    except OSError as exc:
        errors.append(_path_error(path, "FILE_STAT_ERROR", exc))
        return

    if stat_result.st_size > config.max_file_size_bytes:
        errors.append(
            MarkdownScanError(
                path=path,
                code="FILE_TOO_LARGE",
                message=(
                    f"Markdown 文件超过大小上限: "
                    f"{stat_result.st_size} > {config.max_file_size_bytes}"
                ),
            )
        )
        return

    files.append(
        MarkdownFile(
            path=resolved_path,
            relative_path=_relative_posix_path(resolved_path, config.root),
            size_bytes=stat_result.st_size,
        )
    )


def _should_skip_path(path: Path, *, is_dir: bool, config: KnowledgeRepositoryConfig) -> bool:
    relative_path = _relative_posix_path(path, config.root)
    parts = relative_path.split("/")

    if not relative_path:
        return False
    if len(parts) == 1 and not is_dir and path.name == ROOT_README_FILE_NAME:
        return True
    if ASSETS_DIR_NAME in parts:
        return True
    if not config.include_drafts and DRAFTS_DIR_NAME in parts:
        return True
    if not config.include_archive and ARCHIVE_DIR_NAME in parts:
        return True

    return _matches_ignore_patterns(relative_path, is_dir=is_dir, patterns=config.ignore_patterns)


def _matches_ignore_patterns(
    relative_path: str,
    *,
    is_dir: bool,
    patterns: Iterable[str],
) -> bool:
    path_with_dir_suffix = f"{relative_path}/" if is_dir else relative_path
    name = relative_path.rsplit("/", maxsplit=1)[-1]

    for pattern in patterns:
        normalized = pattern.strip().replace("\\", "/")
        if not normalized:
            continue
        if normalized.endswith("/"):
            directory_pattern = normalized.rstrip("/")
            if _path_has_directory(relative_path, directory_pattern, is_dir=is_dir):
                return True
            continue
        if "/" in normalized:
            if fnmatch.fnmatchcase(relative_path, normalized):
                return True
            if fnmatch.fnmatchcase(path_with_dir_suffix, normalized):
                return True
            continue
        if fnmatch.fnmatchcase(name, normalized):
            return True

    return False


def _path_has_directory(relative_path: str, directory_pattern: str, *, is_dir: bool) -> bool:
    parts = relative_path.split("/")
    directory_parts = parts if is_dir else parts[:-1]
    return any(fnmatch.fnmatchcase(part, directory_pattern) for part in directory_parts)


def _relative_posix_path(path: Path, root: Path) -> str:
    try:
        relative = path.relative_to(root)
    except ValueError:
        relative = path.resolve(strict=False).relative_to(root)
    return relative.as_posix()


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _path_error(path: Path, code: str, exc: OSError) -> MarkdownScanError:
    return MarkdownScanError(path=path, code=code, message=f"{exc.__class__.__name__}: {exc}")
