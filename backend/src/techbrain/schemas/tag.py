"""Knowledge tag query API schemas."""

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


class TagSummaryResponse(BaseModel):
    """Tag detail and active document usage count."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    normalized_name: str
    status: str
    usage_count: int
    created_at: datetime
    updated_at: datetime


class TagListResponse(BaseModel):
    """Paginated tag list response."""

    items: list[TagSummaryResponse] = Field(default_factory=list)
    pagination: PaginationResponse


class TagDocumentResponse(BaseModel):
    """Document summary returned from a tag association query."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: str
    title: str
    summary: str | None
    category_id: int
    category: str
    status: str
    source_updated_at: datetime
    relative_path: str


class TagDocumentListResponse(BaseModel):
    """Paginated documents associated with one tag."""

    items: list[TagDocumentResponse] = Field(default_factory=list)
    pagination: PaginationResponse
