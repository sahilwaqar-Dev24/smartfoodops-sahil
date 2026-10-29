from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.restaurant import Restaurant
from app.models.user import User
from app.schemas.analytics import AnalyticsSummaryResponse, SearchResponse
from app.services.analytics_service import (
    get_platform_analytics,
    get_restaurant_analytics,
    search_menu_items_tfidf,
)

router = APIRouter(tags=["Analytics & Search"])


@router.get(
    "/analytics/platform",
    response_model=AnalyticsSummaryResponse,
    summary="Platform-wide aggregated analytics",
)
def view_platform_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "restaurant_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only restaurant admins are authorized to view platform analytics",
        )
    return get_platform_analytics(db=db)


@router.get(
    "/analytics/restaurants/{restaurant_id}",
    response_model=AnalyticsSummaryResponse,
    summary="Restaurant specific analytics",
)
def view_restaurant_analytics(
    restaurant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "restaurant_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only restaurant admins are authorized to view analytics",
        )

    restaurant = (
        db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
    )
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Restaurant with ID {restaurant_id} not found",
        )

    if restaurant.owner_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You can only view analytics for your own restaurant",
        )

    return get_restaurant_analytics(db=db, restaurant_id=restaurant_id)


@router.get(
    "/search/menu-items",
    response_model=SearchResponse,
    summary="Intelligent TF-IDF menu item search",
)
def search_menu_items(
    q: str = Query(..., min_length=1, description="Search query keyword or phrase"),
    max_price: Optional[float] = Query(
        None, gt=0, description="Optional maximum price filter"
    ),
    top_k: int = Query(5, ge=1, le=20, description="Max results to return"),
    db: Session = Depends(get_db),
):
    results = search_menu_items_tfidf(
        db=db, query=q, max_price=max_price, top_k=top_k
    )
    return SearchResponse(query=q, count=len(results), results=results)