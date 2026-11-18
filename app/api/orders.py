from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.order import Order, OrderStatusHistory
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

@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def place_order(
    order_in: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return create_order(db=db, order_in=order_in, customer_id=current_user.id)

@router.get("/", response_model=List[OrderResponse])
def list_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role == "customer":
        return db.query(Order).filter(Order.customer_id == current_user.id).all()
    elif current_user.role == "restaurant_admin":
        return db.query(Order).all()
    elif current_user.role == "rider":
        return db.query(Order).filter(Order.rider_id == current_user.id).all()
    return []

@router.get("/{order_id}", response_model=OrderResponse)
def get_order_details(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if current_user.role == "customer" and order.customer_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access forbidden")
    elif current_user.role == "rider" and order.rider_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access forbidden")
    return order

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
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return (
        db.query(OrderStatusHistory)
        .filter(OrderStatusHistory.order_id == order_id)
        .order_by(OrderStatusHistory.changed_at.asc())
        .all()
    )