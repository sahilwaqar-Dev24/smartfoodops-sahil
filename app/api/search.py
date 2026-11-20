from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.search import SearchResponse
from app.services.search_service import search_menu_items

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("/menu-items", response_model=SearchResponse, summary="Ranked menu item search (TF-IDF)")
def search_items(
    q: str = Query(..., min_length=1, max_length=200, description="e.g. 'spicy chicken under 600'"),
    max_price: Optional[float] = Query(None, gt=0, description="Optional maximum price"),
    cuisine: Optional[str] = Query(None, description="Optional cuisine filter, e.g. Desi"),
    top_k: int = Query(5, ge=1, le=20, description="Number of results (default 5)"),
    db: Session = Depends(get_db),
):
    results = search_menu_items(db, query=q, max_price=max_price, cuisine=cuisine, top_k=top_k)
    return SearchResponse(query=q, max_price=max_price, cuisine=cuisine, count=len(results), results=results)