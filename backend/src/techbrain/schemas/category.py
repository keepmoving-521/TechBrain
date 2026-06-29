"""Knowledge category API schemas."""

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


class CategoryCreateRequest(BaseModel):
    """Create an empty category."""

    name: str = Field(min_length=1, max_length=80)
    slug: str = Field(min_length=1, max_length=80)
    parent_id: int | None = Field(default=None, ge=1)
    sort_order: int = Field(default=0, ge=0)


class CategoryUpdateRequest(BaseModel):
    """Rename, move or reorder one category."""

    name: str | None = Field(default=None, min_length=1, max_length=80)
    slug: str | None = Field(default=None, min_length=1, max_length=80)
    parent_id: int | None = Field(default=None, ge=1)
    sort_order: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def reject_null_non_nullable_updates(self) -> "CategoryUpdateRequest":
        """Allow null only for parent_id, where it means move to the root."""
        for field_name in ("name", "slug", "sort_order"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} 不能为 null")
        return self


class CategoryDocumentMigrationRequest(BaseModel):
    """Move all direct documents to another category."""

    target_category_id: int = Field(ge=1)


class CategoryDocumentMigrationResponse(BaseModel):
    """Category document migration result."""

    model_config = ConfigDict(from_attributes=True)

    source_category_id: int
    target_category_id: int
    migrated_count: int
