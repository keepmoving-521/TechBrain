"""Knowledge document list API schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PaginationResponse(BaseModel):
    """Standard page metadata."""

    model_config = ConfigDict(from_attributes=True)

    page: int
    page_size: int
    total: int
    total_pages: int
    has_previous: bool
    has_next: bool


class DocumentListItemResponse(BaseModel):
    """Knowledge document summary for list and browse pages."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: str
    title: str
    summary: str | None
    category_id: int
    category: str
    tags: list[str] = Field(default_factory=list)
    status: str
    visibility: str
    language: str
    created_at: datetime
    updated_at: datetime
    relative_path: str


class DocumentListResponse(BaseModel):
    """Paginated document list response."""

    items: list[DocumentListItemResponse] = Field(default_factory=list)
    pagination: PaginationResponse
