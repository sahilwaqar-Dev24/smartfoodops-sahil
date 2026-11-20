from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_restaurant_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.analytics import (
    AnalyticsSummaryResponse,
    RestaurantOrderCount,
)
from app.services import restaurant_service
from app.services.analytics_service import (
    get_analytics_summary,
    get_orders_per_restaurant,
    get_owned_restaurant_ids,
)

router = APIRouter(tags=["Analytics"])


def check_date_range(
    date_from: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[date] = Query(None, description="End date (YYYY-MM-DD), inclusive"),
):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_from cannot be after date_to",
        )
    return {"date_from": date_from, "date_to": date_to}


@router.get(
    "/analytics/platform",
    response_model=AnalyticsSummaryResponse,
    summary="Analytics for all of my restaurants",
)
def view_platform_analytics(
    dates: dict = Depends(check_date_range),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_restaurant_admin),
):
    restaurant_ids = get_owned_restaurant_ids(db, current_user)
    return get_analytics_summary(db, restaurant_ids, **dates)


@router.get(
    "/analytics/orders-per-restaurant",
    response_model=List[RestaurantOrderCount],
    summary="Orders per restaurant (my restaurants)",
)
def view_orders_per_restaurant(
    dates: dict = Depends(check_date_range),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_restaurant_admin),
):
    restaurant_ids = get_owned_restaurant_ids(db, current_user)
    return get_orders_per_restaurant(db, restaurant_ids, **dates)


@router.get(
    "/analytics/restaurants/{restaurant_id}",
    response_model=AnalyticsSummaryResponse,
    summary="Analytics for one restaurant",
)
def view_restaurant_analytics(
    restaurant_id: int,
    dates: dict = Depends(check_date_range),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_restaurant_admin),
):
    # 404 agar restaurant nahi, 403 agar kisi aur ka hai
    restaurant_service.get_owned_restaurant(db, restaurant_id, current_user)
    return get_analytics_summary(db, [restaurant_id], **dates)