"""Knowledge category query endpoints."""

from fastapi import APIRouter, Request, status
from starlette.exceptions import HTTPException

from techbrain.db.session import DatabaseManager
from techbrain.knowledge.category_query import get_category_detail, list_category_tree
from techbrain.schemas.category import CategoryDetailResponse, CategoryTreeResponse

router = APIRouter()


@router.get("/tree", response_model=CategoryTreeResponse)
def get_category_tree(request: Request) -> CategoryTreeResponse:
    """Return the complete category tree with active document counts."""
    database: DatabaseManager = request.app.state.database
    with database.session_factory() as session:
        nodes = list_category_tree(session)
        return CategoryTreeResponse(items=list(nodes))


@router.get("/{category_id}", response_model=CategoryDetailResponse)
def get_category(request: Request, category_id: int) -> CategoryDetailResponse:
    """Return one category with immediate parent and child navigation."""
    database: DatabaseManager = request.app.state.database
    with database.session_factory() as session:
        category = get_category_detail(session, category_id)
        if category is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="分类不存在",
            )
        return CategoryDetailResponse.model_validate(category)
