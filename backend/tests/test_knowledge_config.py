"""Knowledge repository configuration tests."""

import uuid
from pathlib import Path

import pytest

from techbrain.core.config import Environment, Settings, get_settings
from techbrain.knowledge.config import (
    DEFAULT_IGNORE_PATTERNS,
    KnowledgeConfigurationError,
    build_knowledge_repository_config,
)


def _test_repo_root() -> Path:
    root = Path(".pytest_tmp") / f"knowledge_{uuid.uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def test_build_knowledge_repository_config_loads_ignore_rules() -> None:
    root = _test_repo_root()
    (root / ".techbrainignore").write_text(
        "# local ignores\nprivate/\n*.secret.md\n\n",
        encoding="utf-8",
    )
    settings = Settings(
        environment=Environment.TEST,
        knowledge_root=root,
        knowledge_extra_ignore_patterns="generated/,*.cache.md",
    )

    config = build_knowledge_repository_config(settings)

    assert config.root == root
    assert config.file_encoding == "utf-8"
    assert config.ignore_file_name == ".techbrainignore"
    assert ".git/" in config.ignore_patterns
    assert "private/" in config.ignore_patterns
    assert "*.secret.md" in config.ignore_patterns
    assert "generated/" in config.ignore_patterns
    assert "*.cache.md" in config.ignore_patterns
    assert len(config.ignore_patterns) == len(set(config.ignore_patterns))


def test_build_knowledge_repository_config_rejects_missing_root() -> None:
    settings = Settings(environment=Environment.TEST, knowledge_root=None)

    with pytest.raises(KnowledgeConfigurationError, match="TECHBRAIN_KNOWLEDGE_ROOT"):
        build_knowledge_repository_config(settings)


def test_build_knowledge_repository_config_rejects_non_existing_root() -> None:
    settings = Settings(
        environment=Environment.TEST,
        knowledge_root=Path(".pytest_tmp") / "missing-knowledge-root",
    )

    with pytest.raises(KnowledgeConfigurationError, match="知识库根目录不存在"):
        build_knowledge_repository_config(settings)


def test_build_knowledge_repository_config_rejects_file_root() -> None:
    root_file = Path(".pytest_tmp") / f"knowledge_file_{uuid.uuid4().hex}.md"
    root_file.parent.mkdir(parents=True, exist_ok=True)
    root_file.write_text("# not a directory", encoding="utf-8")
    settings = Settings(environment=Environment.TEST, knowledge_root=root_file)

    with pytest.raises(KnowledgeConfigurationError, match="不是目录"):
        build_knowledge_repository_config(settings)


def test_build_knowledge_repository_config_rejects_invalid_ignore_file_name() -> None:
    root = _test_repo_root()
    settings = Settings(
        environment=Environment.TEST,
        knowledge_root=root,
        knowledge_ignore_file_name="config/.ignore",
    )

    with pytest.raises(KnowledgeConfigurationError, match="路径分隔符"):
        build_knowledge_repository_config(settings)


def test_build_knowledge_repository_config_rejects_invalid_ignore_encoding() -> None:
    root = _test_repo_root()
    (root / ".techbrainignore").write_bytes(b"\xff\xfe\x00")
    settings = Settings(environment=Environment.TEST, knowledge_root=root)

    with pytest.raises(KnowledgeConfigurationError, match="无法使用 utf-8 解码"):
        build_knowledge_repository_config(settings)


def test_default_ignore_patterns_are_stable() -> None:
    assert ".git/" in DEFAULT_IGNORE_PATTERNS
    assert "node_modules/" in DEFAULT_IGNORE_PATTERNS
    assert "*.tmp" in DEFAULT_IGNORE_PATTERNS


def test_settings_reload_knowledge_root_from_environment(monkeypatch) -> None:
    first_root = _test_repo_root()
    second_root = _test_repo_root()

    monkeypatch.setenv("TECHBRAIN_KNOWLEDGE_ROOT", str(first_root))
    get_settings.cache_clear()
    first_settings = get_settings()

    monkeypatch.setenv("TECHBRAIN_KNOWLEDGE_ROOT", str(second_root))
    get_settings.cache_clear()
    second_settings = get_settings()

    try:
        assert first_settings.knowledge_root == first_root
        assert second_settings.knowledge_root == second_root
    finally:
        get_settings.cache_clear()
