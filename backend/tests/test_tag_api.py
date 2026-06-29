"""Knowledge tag query API tests."""

from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from techbrain.core.config import Environment, Settings
from techbrain.db.base import Base
from techbrain.knowledge.scanner import MarkdownFile
from techbrain.knowledge.sync import sync_markdown_document
from techbrain.models import (
    KnowledgeDocument,
    KnowledgeTag,
    KnowledgeTagStatus,
    knowledge_document_tags,
)


def _write_markdown(
    root: Path,
    file_name: str,
    document_id: str,
    *,
    tags: tuple[str, ...],
    updated_at: str,
) -> MarkdownFile:
    path = root / "backend/python" / file_name
    path.parent.mkdir(parents=True, exist_ok=True)
    tags_yaml = "\n".join(f"  - {tag}" for tag in tags)
    path.write_text(
        f"""---
schema_version: 1
id: {document_id}
title: {document_id} title
category: backend/python
tags:
{tags_yaml}
created_at: 2026-06-29T09:00:00+08:00
updated_at: {updated_at}
summary: {document_id} summary
---

# {document_id}
""",
        encoding="utf-8",
    )
    return MarkdownFile(
        path=path.resolve(),
        relative_path=f"backend/python/{file_name}",
        size_bytes=path.stat().st_size,
    )


def _seed_tags(app) -> dict[str, int]:
    root = Path(".pytest_tmp") / "tag_api"
    Base.metadata.create_all(app.state.database.engine)
    old_file = _write_markdown(
        root,
        "orm-old.md",
        "orm-old",
        tags=("ORM", "performance"),
        updated_at="2026-06-29T10:00:00+08:00",
    )
    new_file = _write_markdown(
        root,
        "orm-new.md",
        "orm-new",
        tags=("orm", "database"),
        updated_at="2026-06-29T12:00:00+08:00",
    )
    deleted_file = _write_markdown(
        root,
        "orm-deleted.md",
        "orm-deleted",
        tags=("orm",),
        updated_at="2026-06-29T13:00:00+08:00",
    )

    with app.state.database.session_factory() as session:
        sync_markdown_document(session, old_file)
        sync_markdown_document(session, new_file)
        deleted = sync_markdown_document(session, deleted_file)
        assert deleted.document is not None
        deleted.document.is_deleted = True
        empty = KnowledgeTag(name="empty", status=KnowledgeTagStatus.ARCHIVED.value)
        session.add(empty)
        session.commit()

        tags = session.scalars(select(KnowledgeTag)).all()
        return {tag.normalized_name: tag.id for tag in tags}


def test_list_tags_sorts_by_name_and_returns_standard_pagination(app) -> None:
    _seed_tags(app)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/v1/tags?page=1&page_size=2&sort=name")

    assert response.status_code == 200
    payload = response.json()
    assert [item["normalized_name"] for item in payload["items"]] == ["database", "empty"]
    assert [item["usage_count"] for item in payload["items"]] == [1, 0]
    assert payload["pagination"] == {
        "page": 1,
        "page_size": 2,
        "total": 4,
        "total_pages": 2,
        "has_previous": False,
        "has_next": True,
    }


def test_list_tags_sorts_by_usage_count_and_supports_descending_name(app) -> None:
    _seed_tags(app)

    with TestClient(app, raise_server_exceptions=False) as client:
        usage_response = client.get("/api/v1/tags?sort=-usage_count")
        name_response = client.get("/api/v1/tags?sort=-name")

    assert usage_response.status_code == 200
    assert [item["normalized_name"] for item in usage_response.json()["items"]] == [
        "orm",
        "database",
        "performance",
        "empty",
    ]
    assert [item["usage_count"] for item in usage_response.json()["items"]] == [2, 1, 1, 0]
    assert [item["normalized_name"] for item in name_response.json()["items"]] == [
        "performance",
        "orm",
        "empty",
        "database",
    ]


def test_get_tag_detail_returns_usage_count_excluding_deleted_documents(app) -> None:
    ids = _seed_tags(app)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(f"/api/v1/tags/{ids['orm']}")

    assert response.status_code == 200
    assert response.json()["normalized_name"] == "orm"
    assert response.json()["usage_count"] == 2
    assert response.json()["status"] == "active"


def test_list_tag_documents_is_paginated_and_excludes_deleted_documents(app) -> None:
    ids = _seed_tags(app)

    with TestClient(app, raise_server_exceptions=False) as client:
        first_page = client.get(f"/api/v1/tags/{ids['orm']}/documents?page=1&page_size=1")
        second_page = client.get(f"/api/v1/tags/{ids['orm']}/documents?page=2&page_size=1")

    assert first_page.status_code == 200
    assert [item["document_id"] for item in first_page.json()["items"]] == ["orm-new"]
    assert first_page.json()["pagination"]["total"] == 2
    assert first_page.json()["pagination"]["total_pages"] == 2
    assert first_page.json()["pagination"]["has_next"] is True
    assert [item["document_id"] for item in second_page.json()["items"]] == ["orm-old"]
    assert second_page.json()["pagination"]["has_previous"] is True


def test_empty_tag_returns_zero_usage_and_empty_document_page(app) -> None:
    ids = _seed_tags(app)

    with TestClient(app, raise_server_exceptions=False) as client:
        detail = client.get(f"/api/v1/tags/{ids['empty']}")
        documents = client.get(f"/api/v1/tags/{ids['empty']}/documents")

    assert detail.status_code == 200
    assert detail.json()["usage_count"] == 0
    assert documents.status_code == 200
    assert documents.json()["items"] == []
    assert documents.json()["pagination"]["total"] == 0
    assert documents.json()["pagination"]["total_pages"] == 0


def test_tag_queries_return_404_and_validate_sort(app) -> None:
    _seed_tags(app)

    with TestClient(app, raise_server_exceptions=False) as client:
        detail = client.get("/api/v1/tags/9999")
        documents = client.get("/api/v1/tags/9999/documents")
        invalid_sort = client.get("/api/v1/tags?sort=created_at")

    assert detail.status_code == 404
    assert detail.json()["error"]["message"] == "标签不存在"
    assert documents.status_code == 404
    assert invalid_sort.status_code == 422
    assert invalid_sort.json()["error"]["code"] == "VALIDATION_ERROR"


def test_create_rename_and_delete_unused_tag(app) -> None:
    Base.metadata.create_all(app.state.database.engine)

    with TestClient(app, raise_server_exceptions=False) as client:
        created = client.post("/api/v1/tags", json={"name": "  Cache  "})
        tag_id = created.json()["id"]
        renamed = client.patch(f"/api/v1/tags/{tag_id}", json={"name": "Caching"})
        unchanged = client.patch(f"/api/v1/tags/{tag_id}", json={"name": "Caching"})
        deleted = client.delete(f"/api/v1/tags/{tag_id}")
        detail = client.get(f"/api/v1/tags/{tag_id}")

    assert created.status_code == 201
    assert created.json()["name"] == "Cache"
    assert created.json()["normalized_name"] == "cache"
    assert created.json()["usage_count"] == 0
    assert renamed.status_code == 200
    assert renamed.json()["id"] == tag_id
    assert renamed.json()["normalized_name"] == "caching"
    assert unchanged.status_code == 200
    assert unchanged.json()["id"] == tag_id
    assert deleted.status_code == 204
    assert detail.status_code == 404


def test_create_and_rename_tag_reject_normalized_name_conflicts(app) -> None:
    Base.metadata.create_all(app.state.database.engine)

    with TestClient(app, raise_server_exceptions=False) as client:
        orm = client.post("/api/v1/tags", json={"name": "ORM"})
        duplicate = client.post(
            "/api/v1/tags",
            json={"name": "\uff4f\uff52\uff4d"},
        )
        database = client.post("/api/v1/tags", json={"name": "database"})
        rename_conflict = client.patch(
            f"/api/v1/tags/{orm.json()['id']}",
            json={"name": "DATABASE"},
        )

    assert orm.status_code == 201
    assert database.status_code == 201
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["message"] == "标签规范化名称已存在: orm"
    assert rename_conflict.status_code == 409
    assert rename_conflict.json()["error"]["message"] == "标签规范化名称已存在: database"


def test_rename_used_tag_rewrites_all_markdown_and_preserves_identity(app) -> None:
    root = Path(".pytest_tmp") / "tag_management_rename"
    app.state.settings = Settings(
        environment=Environment.TEST,
        database_url="sqlite+pysqlite:///:memory:",
        knowledge_root=root.resolve(),
    )
    Base.metadata.create_all(app.state.database.engine)
    first_file = _write_markdown(
        root,
        "rename-first.md",
        "rename-first",
        tags=("ORM", "performance"),
        updated_at="2026-06-29T10:00:00+08:00",
    )
    second_file = _write_markdown(
        root,
        "rename-second.md",
        "rename-second",
        tags=("orm",),
        updated_at="2026-06-29T11:00:00+08:00",
    )
    with app.state.database.session_factory() as session:
        first = sync_markdown_document(session, first_file)
        sync_markdown_document(session, second_file)
        session.commit()
        assert first.document is not None
        tag_id = next(tag.id for tag in first.document.tag_nodes if tag.normalized_name == "orm")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.patch(
            f"/api/v1/tags/{tag_id}",
            json={"name": "object-relational-mapping"},
        )
        with app.state.database.session_factory() as session:
            tag = session.get(KnowledgeTag, tag_id)
            documents = session.execute(
                select(KnowledgeTag.id, KnowledgeTag.normalized_name).where(
                    KnowledgeTag.id == tag_id
                )
            ).one()
            document_tags = session.scalars(
                select(KnowledgeTag.normalized_name)
                .join(KnowledgeTag.documents)
                .where(KnowledgeTag.id == tag_id)
            ).all()

    assert response.status_code == 200
    assert response.json()["id"] == tag_id
    assert response.json()["normalized_name"] == "object-relational-mapping"
    assert response.json()["usage_count"] == 2
    assert tag is not None
    assert documents == (tag_id, "object-relational-mapping")
    assert document_tags == ["object-relational-mapping", "object-relational-mapping"]
    assert '  - "object-relational-mapping"\n' in first_file.path.read_text(encoding="utf-8")
    assert '  - "object-relational-mapping"\n' in second_file.path.read_text(encoding="utf-8")
    assert "updated_at: 2026-06-29T10:00:00+08:00" not in first_file.path.read_text(
        encoding="utf-8"
    )


def test_delete_used_tag_is_rejected(app) -> None:
    ids = _seed_tags(app)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.delete(f"/api/v1/tags/{ids['orm']}")

    assert response.status_code == 409
    assert response.json()["error"]["message"] == "标签正在被文档使用, 无法直接删除"


def test_rename_tag_rejects_external_markdown_modification(app) -> None:
    root = Path(".pytest_tmp") / "tag_management_conflict"
    app.state.settings = Settings(
        environment=Environment.TEST,
        database_url="sqlite+pysqlite:///:memory:",
        knowledge_root=root.resolve(),
    )
    Base.metadata.create_all(app.state.database.engine)
    markdown_file = _write_markdown(
        root,
        "external.md",
        "tag-external-change",
        tags=("orm",),
        updated_at="2026-06-29T10:00:00+08:00",
    )
    with app.state.database.session_factory() as session:
        synced = sync_markdown_document(session, markdown_file)
        session.commit()
        assert synced.document is not None
        tag_id = synced.document.tag_nodes[0].id

    external_content = markdown_file.path.read_text(encoding="utf-8").replace(
        "# tag-external-change",
        "# externally changed",
    )
    markdown_file.path.write_text(external_content, encoding="utf-8")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.patch(f"/api/v1/tags/{tag_id}", json={"name": "database-orm"})
        with app.state.database.session_factory() as session:
            tag = session.get(KnowledgeTag, tag_id)
            assert tag is not None
            normalized_name = tag.normalized_name

    assert response.status_code == 409
    assert "已被外部修改" in response.json()["error"]["message"]
    assert normalized_name == "orm"
    assert "# externally changed" in markdown_file.path.read_text(encoding="utf-8")
    assert "  - orm\n" in markdown_file.path.read_text(encoding="utf-8")


def test_tag_management_returns_not_found_and_validation_errors(app) -> None:
    Base.metadata.create_all(app.state.database.engine)

    with TestClient(app, raise_server_exceptions=False) as client:
        missing_rename = client.patch("/api/v1/tags/9999", json={"name": "missing"})
        missing_delete = client.delete("/api/v1/tags/9999")
        invalid_name = client.post("/api/v1/tags", json={"name": "line\nbreak"})

    assert missing_rename.status_code == 404
    assert missing_delete.status_code == 404
    assert invalid_name.status_code == 400
    assert invalid_name.json()["error"]["message"] == "标签名称不能包含控制字符"


def test_tag_management_rejects_write_while_sync_lock_is_held(app) -> None:
    Base.metadata.create_all(app.state.database.engine)
    app.state.knowledge_sync_lock.acquire()
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/api/v1/tags", json={"name": "blocked"})
    finally:
        app.state.knowledge_sync_lock.release()

    assert response.status_code == 409
    assert "正在执行" in response.json()["error"]["message"]


def test_merge_tags_migrates_all_documents_without_duplicate_relations(app) -> None:
    root = Path(".pytest_tmp") / "tag_merge_success"
    app.state.settings = Settings(
        environment=Environment.TEST,
        database_url="sqlite+pysqlite:///:memory:",
        knowledge_root=root.resolve(),
    )
    Base.metadata.create_all(app.state.database.engine)
    source_file = _write_markdown(
        root,
        "merge-source.md",
        "merge-source",
        tags=("orm",),
        updated_at="2026-06-29T10:00:00+08:00",
    )
    both_file = _write_markdown(
        root,
        "merge-both.md",
        "merge-both",
        tags=("orm", "database"),
        updated_at="2026-06-29T11:00:00+08:00",
    )
    target_file = _write_markdown(
        root,
        "merge-target.md",
        "merge-target",
        tags=("database",),
        updated_at="2026-06-29T12:00:00+08:00",
    )
    with app.state.database.session_factory() as session:
        source_result = sync_markdown_document(session, source_file)
        both_result = sync_markdown_document(session, both_file)
        sync_markdown_document(session, target_file)
        session.commit()
        assert source_result.document is not None
        assert both_result.document is not None
        source_id = next(
            tag.id for tag in source_result.document.tag_nodes if tag.normalized_name == "orm"
        )
        target_id = next(
            tag.id for tag in both_result.document.tag_nodes if tag.normalized_name == "database"
        )

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            f"/api/v1/tags/{source_id}/merge",
            json={"target_tag_id": target_id},
        )
        source_detail = client.get(f"/api/v1/tags/{source_id}")
        target_detail = client.get(f"/api/v1/tags/{target_id}")
        with app.state.database.session_factory() as session:
            source = session.get(KnowledgeTag, source_id)
            document_tags = session.scalars(
                select(KnowledgeDocument.tags).order_by(KnowledgeDocument.document_id)
            ).all()
            source_link_count = len(
                session.execute(
                    select(knowledge_document_tags).where(
                        knowledge_document_tags.c.tag_id == source_id
                    )
                ).all()
            )
            target_link_count = len(
                session.execute(
                    select(knowledge_document_tags).where(
                        knowledge_document_tags.c.tag_id == target_id
                    )
                ).all()
            )

    assert response.status_code == 200
    assert response.json() == {
        "source_tag_id": source_id,
        "target_tag_id": target_id,
        "migrated_document_count": 2,
        "source_status": "archived",
    }
    assert source is not None
    assert source.status == KnowledgeTagStatus.ARCHIVED.value
    assert source_detail.json()["usage_count"] == 0
    assert target_detail.json()["usage_count"] == 3
    assert document_tags == [["database"], ["database"], ["database"]]
    assert source_link_count == 0
    assert target_link_count == 3
    assert source_file.path.read_text(encoding="utf-8").count('  - "database"') == 1
    assert both_file.path.read_text(encoding="utf-8").count('  - "database"') == 1
    assert "orm" not in source_file.path.read_text(encoding="utf-8")
    assert "orm" not in both_file.path.read_text(encoding="utf-8")


def test_merge_tags_rejects_same_or_missing_target(app) -> None:
    Base.metadata.create_all(app.state.database.engine)
    with app.state.database.session_factory() as session:
        source = KnowledgeTag(name="source", status=KnowledgeTagStatus.ACTIVE.value)
        session.add(source)
        session.commit()
        source_id = source.id

    with TestClient(app, raise_server_exceptions=False) as client:
        same = client.post(
            f"/api/v1/tags/{source_id}/merge",
            json={"target_tag_id": source_id},
        )
        missing = client.post(
            f"/api/v1/tags/{source_id}/merge",
            json={"target_tag_id": 9999},
        )
        missing_source = client.post(
            "/api/v1/tags/9998/merge",
            json={"target_tag_id": source_id},
        )

    assert same.status_code == 409
    assert same.json()["error"]["message"] == "源标签和目标标签不能相同"
    assert missing.status_code == 404
    assert missing.json()["error"]["message"] == "目标标签不存在"
    assert missing_source.status_code == 404
    assert missing_source.json()["error"]["message"] == "源标签不存在"


def test_merge_unused_tag_archives_source_and_activates_target(app) -> None:
    Base.metadata.create_all(app.state.database.engine)
    with app.state.database.session_factory() as session:
        source = KnowledgeTag(name="unused-source", status=KnowledgeTagStatus.ACTIVE.value)
        target = KnowledgeTag(name="unused-target", status=KnowledgeTagStatus.ARCHIVED.value)
        session.add_all((source, target))
        session.commit()
        source_id = source.id
        target_id = target.id

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            f"/api/v1/tags/{source_id}/merge",
            json={"target_tag_id": target_id},
        )
        source_detail = client.get(f"/api/v1/tags/{source_id}")
        target_detail = client.get(f"/api/v1/tags/{target_id}")

    assert response.status_code == 200
    assert response.json()["migrated_document_count"] == 0
    assert response.json()["source_status"] == "archived"
    assert source_detail.json()["status"] == "archived"
    assert target_detail.json()["status"] == "active"


def test_merge_tag_rejects_soft_deleted_source_document(app) -> None:
    root = Path(".pytest_tmp") / "tag_merge_deleted_document"
    Base.metadata.create_all(app.state.database.engine)
    markdown_file = _write_markdown(
        root,
        "deleted-source.md",
        "merge-deleted-source",
        tags=("source-tag",),
        updated_at="2026-06-29T10:00:00+08:00",
    )
    with app.state.database.session_factory() as session:
        synced = sync_markdown_document(session, markdown_file)
        target = KnowledgeTag(name="target-tag", status=KnowledgeTagStatus.ACTIVE.value)
        session.add(target)
        assert synced.document is not None
        synced.document.is_deleted = True
        session.commit()
        source_id = synced.document.tag_nodes[0].id
        target_id = target.id

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            f"/api/v1/tags/{source_id}/merge",
            json={"target_tag_id": target_id},
        )

    assert response.status_code == 409
    assert response.json()["error"]["message"] == "源标签关联了源文件已删除的文档, 无法安全合并"
