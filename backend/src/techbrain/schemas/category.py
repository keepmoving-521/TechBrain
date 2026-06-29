"""Knowledge category API schemas."""

from pydantic import BaseModel, ConfigDict, Field


class CategorySummaryResponse(BaseModel):
    """Common category fields and document counts."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    parent_id: int | None
    name: str
    slug: str
    path: str
    sort_order: int
    status: str
    direct_document_count: int
    document_count: int


class CategoryTreeNodeResponse(CategorySummaryResponse):
    """Recursive category tree node response."""

    children: list["CategoryTreeNodeResponse"] = Field(default_factory=list)


class CategoryTreeResponse(BaseModel):
    """Category tree response envelope."""

    items: list[CategoryTreeNodeResponse] = Field(default_factory=list)


class CategoryDetailResponse(CategorySummaryResponse):
    """Category detail with immediate parent and children."""

    parent: CategorySummaryResponse | None = None
    children: list[CategorySummaryResponse] = Field(default_factory=list)
