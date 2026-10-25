from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.models.user import User
from app.models.order import Order, OrderStatus
from app.models.restaurant import Restaurant
from app.schemas.order import (
    OrderCreate,
    OrderResponse,
    OrderStatusUpdate,
    OrderStatusHistoryResponse
)
from app.api.deps import get_current_user, require_restaurant_admin
from app.services.order_service import create_order, transition_order_status

router = APIRouter(prefix="/orders", tags=["Orders & Checkout"])


# 1. Customer places order
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
    return create_order(db=db, customer_id=current_user.id, order_in=order_in)


# 2. Get customer's orders or restaurant's orders
@router.get("/", response_model=List[OrderResponse])
def list_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role == "customer":
        return db.query(Order).filter(Order.customer_id == current_user.id).order_by(Order.created_at.desc()).all()
    elif current_user.role == "restaurant_admin":
        return (
            db.query(Order)
            .join(Restaurant, Order.restaurant_id == Restaurant.id)
            .filter(Restaurant.owner_user_id == current_user.id)
            .order_by(Order.created_at.desc())
            .all()
        )
    else:
        return db.query(Order).order_by(Order.created_at.desc()).all()


# 3. Get single order details
@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    # Access control
    if current_user.role == "customer" and order.customer_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if current_user.role == "restaurant_admin" and order.restaurant.owner_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return order


# 4. Status Transition Endpoint (Restaurant Admin updates status: ACCEPTED, PREPARING, READY, etc.)
@router.patch("/{order_id}/status", response_model=OrderResponse)
def update_order_status(
    order_id: int,
    status_in: OrderStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_restaurant_admin)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    if order.restaurant.owner_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only manage orders for your own restaurant"
        )

    return transition_order_status(db=db, order=order, new_status=status_in.status, user_id=current_user.id)


# 5. Order Status History (Audit trail)
@router.get("/{order_id}/history", response_model=List[OrderStatusHistoryResponse])
def get_order_history(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    if current_user.role == "customer" and order.customer_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if current_user.role == "restaurant_admin" and order.restaurant.owner_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return order.status_history