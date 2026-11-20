from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.order import Order, OrderStatus, OrderStatusHistory
from app.models.restaurant import Restaurant
from app.schemas.order import (
    OrderCreate,
    OrderResponse,
    OrderStatusUpdate,
    OrderStatusHistoryResponse,
    OrderAssignRider
)
from app.services.order_service import (
    create_order,
    update_order_status,
    assign_rider_to_order
)

router = APIRouter(prefix="/orders", tags=["Orders"])


def get_order_or_403(order_id: int, db: Session, current_user: User) -> Order:
    """Order dhoondo aur check karo ke current user ko is order ka access hai."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    if current_user.role == "customer":
        allowed = order.customer_id == current_user.id
    elif current_user.role == "rider":
        allowed = order.rider_id == current_user.id
    elif current_user.role == "restaurant_admin":
        restaurant = db.query(Restaurant).filter(Restaurant.id == order.restaurant_id).first()
        allowed = restaurant is not None and restaurant.owner_user_id == current_user.id
    else:
        allowed = False

    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access forbidden")
    return order


@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def place_order(
    order_in: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "customer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only customers can place orders"
        )
    return create_order(db=db, order_in=order_in, customer_id=current_user.id)


@router.get("/", response_model=List[OrderResponse])
def list_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role == "customer":
        return db.query(Order).filter(Order.customer_id == current_user.id).all()
    elif current_user.role == "restaurant_admin":
        # Sirf apne restaurants ke orders
        return (
            db.query(Order)
            .join(Restaurant, Order.restaurant_id == Restaurant.id)
            .filter(Restaurant.owner_user_id == current_user.id)
            .all()
        )
    elif current_user.role == "rider":
        return db.query(Order).filter(Order.rider_id == current_user.id).all()
    return []


@router.get("/{order_id}", response_model=OrderResponse)
def get_order_details(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return get_order_or_403(order_id, db, current_user)


@router.post("/{order_id}/accept", response_model=OrderResponse)
def accept_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return update_order_status(
        db=db, order_id=order_id, new_status=OrderStatus.ACCEPTED, current_user=current_user
    )


@router.post("/{order_id}/reject", response_model=OrderResponse)
def reject_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return update_order_status(
        db=db, order_id=order_id, new_status=OrderStatus.REJECTED, current_user=current_user
    )


@router.post("/{order_id}/assign-rider", response_model=OrderResponse)
def assign_rider(
    order_id: int,
    payload: Optional[OrderAssignRider] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    rider_id = payload.rider_id if payload else None
    return assign_rider_to_order(db=db, order_id=order_id, current_user=current_user, rider_id=rider_id)


@router.patch("/{order_id}/status", response_model=OrderResponse)
def change_order_status(
    order_id: int,
    status_in: OrderStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return update_order_status(
        db=db,
        order_id=order_id,
        new_status=status_in.status,
        current_user=current_user
    )


@router.get("/{order_id}/history", response_model=List[OrderStatusHistoryResponse])
def get_order_history(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_order_or_403(order_id, db, current_user)
    return (
        db.query(OrderStatusHistory)
        .filter(OrderStatusHistory.order_id == order_id)
        .order_by(OrderStatusHistory.changed_at.asc())
        .all()
    )