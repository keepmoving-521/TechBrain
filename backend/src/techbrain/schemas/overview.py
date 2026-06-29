"""Knowledge homepage API schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OverviewStatisticsResponse(BaseModel):
    """Knowledge summary counts."""

    model_config = ConfigDict(from_attributes=True)

    document_count: int
    published_document_count: int
    draft_document_count: int
    category_count: int
    tag_count: int


class RecentDocumentResponse(BaseModel):
    """Recently updated document entry."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: str
    title: str
    summary: str | None
    category_id: int
    category: str
    tags: list[str] = Field(default_factory=list)
    status: str
    updated_at: datetime


class PopularCategoryResponse(BaseModel):
    """Frequently used category entry."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    path: str
    document_count: int


class PopularTagResponse(BaseModel):
    """Frequently used tag entry."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    usage_count: int


class KnowledgeOverviewResponse(BaseModel):
    """Knowledge homepage response."""

    model_config = ConfigDict(from_attributes=True)

    is_empty: bool
    statistics: OverviewStatisticsResponse
    recent_documents: list[RecentDocumentResponse] = Field(default_factory=list)
    popular_categories: list[PopularCategoryResponse] = Field(default_factory=list)
    popular_tags: list[PopularTagResponse] = Field(default_factory=list)
