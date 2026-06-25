"""Markdown knowledge repository scanner tests."""

import os
import uuid
from pathlib import Path

from techbrain.knowledge.config import KnowledgeRepositoryConfig
from techbrain.knowledge.scanner import scan_markdown_files


def _test_repo_root() -> Path:
    root = Path(".pytest_tmp") / f"scanner_{uuid.uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def _config(
    root: Path,
    *,
    ignore_patterns: tuple[str, ...] = (),
    include_drafts: bool = False,
    include_archive: bool = False,
    max_file_size_bytes: int = 1024,
) -> KnowledgeRepositoryConfig:
    return KnowledgeRepositoryConfig(
        root=root,
        file_encoding="utf-8",
        ignore_file_name=".techbrainignore",
        ignore_patterns=ignore_patterns,
        include_drafts=include_drafts,
        include_archive=include_archive,
        sync_batch_size=100,
        max_file_size_bytes=max_file_size_bytes,
    )


def _write(root: Path, relative_path: str, content: str = "# Note") -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_scan_markdown_files_discovers_valid_markdown_files() -> None:
    root = _test_repo_root()
    _write(root, "backend/python/sqlalchemy-joinedload.md")
    _write(root, "database/mysql/index-optimization.md")
    _write(root, "database/mysql/readme.txt")

    result = scan_markdown_files(_config(root))

    assert [file.relative_path for file in result.files] == [
        "backend/python/sqlalchemy-joinedload.md",
        "database/mysql/index-optimization.md",
    ]
    assert result.errors == ()


def test_scan_markdown_files_skips_special_directories_by_default() -> None:
    root = _test_repo_root()
    _write(root, "README.md")
    _write(root, "assets/readme.md")
    _write(root, "drafts/draft-note.md")
    _write(root, "archive/2025/old-note.md")
    _write(root, "backend/python/official-note.md")

    result = scan_markdown_files(_config(root))

    assert [file.relative_path for file in result.files] == ["backend/python/official-note.md"]


def test_scan_markdown_files_can_include_drafts_and_archive() -> None:
    root = _test_repo_root()
    _write(root, "drafts/draft-note.md")
    _write(root, "archive/2025/old-note.md")

    result = scan_markdown_files(
        _config(root, include_drafts=True, include_archive=True),
    )

    assert [file.relative_path for file in result.files] == [
        "archive/2025/old-note.md",
        "drafts/draft-note.md",
    ]


def test_scan_markdown_files_applies_ignore_patterns() -> None:
    root = _test_repo_root()
    _write(root, "backend/python/visible.md")
    _write(root, "private/secret.md")
    _write(root, "backend/tmp/cache.md")
    _write(root, "backend/python/generated.secret.md")

    result = scan_markdown_files(_config(root, ignore_patterns=("private/", "tmp/", "*.secret.md")))

    assert [file.relative_path for file in result.files] == ["backend/python/visible.md"]


def test_scan_markdown_files_records_large_file_error() -> None:
    root = _test_repo_root()
    _write(root, "backend/python/large-note.md", "# Large\n" + ("x" * 128))

    result = scan_markdown_files(_config(root, max_file_size_bytes=10))

    assert result.files == ()
    assert len(result.errors) == 1
    assert result.errors[0].code == "FILE_TOO_LARGE"
    assert result.errors[0].path.name == "large-note.md"


def test_scan_markdown_files_records_directory_access_error(monkeypatch) -> None:
    root = _test_repo_root()
    blocked = root / "blocked"
    blocked.mkdir()
    _write(root, "backend/python/visible.md")

    original_scandir = os.scandir

    def fake_scandir(path):
        if Path(path) == blocked:
            raise PermissionError("permission denied")
        return original_scandir(path)

    monkeypatch.setattr(os, "scandir", fake_scandir)

    result = scan_markdown_files(_config(root))

    assert [file.relative_path for file in result.files] == ["backend/python/visible.md"]
    assert len(result.errors) == 1
    assert result.errors[0].code == "DIRECTORY_ACCESS_ERROR"
    assert result.errors[0].path == blocked


def test_scan_markdown_files_records_damaged_path_error(monkeypatch) -> None:
    root = _test_repo_root()
    _write(root, "backend/python/broken.md")
    _write(root, "backend/python/visible.md")

    original_resolve = Path.resolve

    def fake_resolve(self, *args, **kwargs):
        if self.name == "broken.md":
            raise OSError("damaged path")
        return original_resolve(self, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", fake_resolve)

    result = scan_markdown_files(_config(root))

    assert [file.relative_path for file in result.files] == ["backend/python/visible.md"]
    assert len(result.errors) == 1
    assert result.errors[0].code == "PATH_RESOLVE_ERROR"
    assert result.errors[0].path.name == "broken.md"
