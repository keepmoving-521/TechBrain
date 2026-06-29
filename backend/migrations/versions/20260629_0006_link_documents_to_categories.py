"""Link knowledge documents to synchronized categories.

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-29 00:00:00.000000
"""

import re
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CATEGORY_PART_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,78}[a-z0-9])?$")
_RESERVED_PARTS = {"assets", "drafts", "archive"}


def upgrade() -> None:
    """Add, backfill and constrain the document category foreign key."""
    op.add_column("knowledge_documents", sa.Column("category_id", sa.Integer(), nullable=True))
    op.create_index(
        "ix_knowledge_documents_category_id",
        "knowledge_documents",
        ["category_id"],
    )

    _backfill_category_links(op.get_bind())

    with op.batch_alter_table("knowledge_documents") as batch_op:
        batch_op.alter_column("category_id", existing_type=sa.Integer(), nullable=False)
        batch_op.create_foreign_key(
            "fk_knowledge_documents_category_id",
            "knowledge_categories",
            ["category_id"],
            ["id"],
            ondelete="RESTRICT",
        )


def downgrade() -> None:
    """Remove the document category relationship."""
    op.drop_index("ix_knowledge_documents_category_id", table_name="knowledge_documents")
    with op.batch_alter_table("knowledge_documents") as batch_op:
        batch_op.drop_constraint("fk_knowledge_documents_category_id", type_="foreignkey")
        batch_op.drop_column("category_id")


def _backfill_category_links(connection: sa.Connection) -> None:
    metadata = sa.MetaData()
    documents = sa.Table("knowledge_documents", metadata, autoload_with=connection)
    categories = sa.Table("knowledge_categories", metadata, autoload_with=connection)

    paths = connection.execute(sa.select(documents.c.category).distinct()).scalars().all()
    category_ids: dict[str, int] = {}
    for path in paths:
        _validate_category_path(path)
        parent_id: int | None = None
        current_parts: list[str] = []
        for segment in path.split("/"):
            current_parts.append(segment)
            current_path = "/".join(current_parts)
            row = connection.execute(
                sa.select(categories.c.id, categories.c.parent_id).where(
                    categories.c.path == current_path
                )
            ).one_or_none()
            if row is None:
                result = connection.execute(
                    categories.insert().values(
                        parent_id=parent_id,
                        name=segment,
                        slug=segment,
                        path=current_path,
                        sort_order=0,
                        status="active",
                    )
                )
                category_id = int(result.inserted_primary_key[0])
            else:
                category_id = int(row.id)
                if row.parent_id != parent_id:
                    raise RuntimeError(f"分类 {current_path!r} 的父子关系与路径不一致")
            parent_id = category_id
        category_ids[path] = parent_id

    for path, category_id in category_ids.items():
        connection.execute(
            documents.update().where(documents.c.category == path).values(category_id=category_id)
        )


def _validate_category_path(path: object) -> None:
    if not isinstance(path, str) or not path or len(path) > 512:
        raise RuntimeError(f"无法迁移非法文档分类路径: {path!r}")
    parts = path.split("/")
    if any(part in _RESERVED_PARTS or not _CATEGORY_PART_PATTERN.fullmatch(part) for part in parts):
        raise RuntimeError(f"无法迁移非法文档分类路径: {path!r}")
