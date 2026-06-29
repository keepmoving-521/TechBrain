"""Read models and queries for knowledge categories."""

from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from techbrain.models import KnowledgeCategory, KnowledgeDocument


@dataclass(frozen=True)
class CategorySummary:
    """Category fields shared by tree and detail responses."""

    id: int
    parent_id: int | None
    name: str
    slug: str
    path: str
    sort_order: int
    status: str
    direct_document_count: int
    document_count: int


@dataclass(frozen=True)
class CategoryTreeNode(CategorySummary):
    """One recursively nested category tree node."""

    children: tuple["CategoryTreeNode", ...] = ()


@dataclass(frozen=True)
class CategoryDetail(CategorySummary):
    """One category with immediate navigation context."""

    parent: CategorySummary | None = None
    children: tuple[CategorySummary, ...] = ()


@dataclass
class _CategoryNode:
    category: KnowledgeCategory
    direct_document_count: int
    children: list["_CategoryNode"] = field(default_factory=list)


def list_category_tree(session: Session) -> tuple[CategoryTreeNode, ...]:
    """Return all categories as a stably sorted tree with document counts."""
    roots, _ = _load_category_nodes(session)
    return tuple(_to_tree_node(root, visiting=set()) for root in roots)


def get_category_detail(session: Session, category_id: int) -> CategoryDetail | None:
    """Return one category with parent, children and recursive document count."""
    _, nodes = _load_category_nodes(session)
    node = nodes.get(category_id)
    if node is None:
        return None

    totals: dict[int, int] = {}
    total = _document_count(node, totals=totals, visiting=set())
    parent = nodes.get(node.category.parent_id) if node.category.parent_id is not None else None
    return CategoryDetail(
        **_summary_values(node, document_count=total),
        parent=(
            CategorySummary(
                **_summary_values(
                    parent,
                    document_count=_document_count(parent, totals=totals, visiting=set()),
                )
            )
            if parent is not None
            else None
        ),
        children=tuple(
            CategorySummary(
                **_summary_values(
                    child,
                    document_count=_document_count(child, totals=totals, visiting=set()),
                )
            )
            for child in node.children
        ),
    )


def _load_category_nodes(
    session: Session,
) -> tuple[list[_CategoryNode], dict[int, _CategoryNode]]:
    direct_counts = dict(
        session.execute(
            select(KnowledgeDocument.category_id, func.count(KnowledgeDocument.id))
            .where(KnowledgeDocument.is_deleted.is_(False))
            .group_by(KnowledgeDocument.category_id)
        ).all()
    )
    categories = session.scalars(
        select(KnowledgeCategory).order_by(
            KnowledgeCategory.sort_order,
            KnowledgeCategory.id,
        )
    ).all()
    nodes = {
        category.id: _CategoryNode(
            category=category,
            direct_document_count=int(direct_counts.get(category.id, 0)),
        )
        for category in categories
    }
    roots: list[_CategoryNode] = []
    for category in categories:
        node = nodes[category.id]
        if category.parent_id is None:
            roots.append(node)
            continue
        parent = nodes.get(category.parent_id)
        if parent is None:
            raise ValueError(f"分类 {category.path!r} 引用了不存在的父分类")
        parent.children.append(node)
    return roots, nodes


def _to_tree_node(node: _CategoryNode, *, visiting: set[int]) -> CategoryTreeNode:
    if node.category.id in visiting:
        raise ValueError(f"分类树存在循环关系: {node.category.path}")
    next_visiting = {*visiting, node.category.id}
    children = tuple(_to_tree_node(child, visiting=next_visiting) for child in node.children)
    document_count = node.direct_document_count + sum(child.document_count for child in children)
    return CategoryTreeNode(
        **_summary_values(node, document_count=document_count),
        children=children,
    )


def _document_count(
    node: _CategoryNode,
    *,
    totals: dict[int, int],
    visiting: set[int],
) -> int:
    category_id = node.category.id
    if category_id in totals:
        return totals[category_id]
    if category_id in visiting:
        raise ValueError(f"分类树存在循环关系: {node.category.path}")
    next_visiting = {*visiting, category_id}
    total = node.direct_document_count + sum(
        _document_count(child, totals=totals, visiting=next_visiting) for child in node.children
    )
    totals[category_id] = total
    return total


def _summary_values(node: _CategoryNode, *, document_count: int) -> dict[str, object]:
    category = node.category
    return {
        "id": category.id,
        "parent_id": category.parent_id,
        "name": category.name,
        "slug": category.slug,
        "path": category.path,
        "sort_order": category.sort_order,
        "status": category.status,
        "direct_document_count": node.direct_document_count,
        "document_count": document_count,
    }
