"""Knowledge homepage endpoint."""

from fastapi import APIRouter, Request

from techbrain.db.session import DatabaseManager
from techbrain.knowledge.overview import get_knowledge_overview
from techbrain.schemas.overview import KnowledgeOverviewResponse

router = APIRouter()


@router.get("", response_model=KnowledgeOverviewResponse)
def get_overview(request: Request) -> KnowledgeOverviewResponse:
    """Return summary counts and homepage navigation entries."""
    database: DatabaseManager = request.app.state.database
    with database.session_factory() as session:
        overview = get_knowledge_overview(session)
        return KnowledgeOverviewResponse.model_validate(overview, from_attributes=True)
