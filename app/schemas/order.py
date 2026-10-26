from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.models.order import OrderStatus

class OrderItemCreate(BaseModel):
    menu_item_id: int
    quantity: int

class OrderCreate(BaseModel):
    restaurant_id: int
    delivery_address: str
    items: List[OrderItemCreate]

class OrderStatusUpdate(BaseModel):
    status: OrderStatus

class OrderAssignRider(BaseModel):
    rider_id: Optional[int] = None

class OrderItemResponse(BaseModel):
    id: int
    menu_item_id: int
    item_name: str
    unit_price: float
    quantity: int
    line_total: float

    class Config:
        from_attributes = True

class OrderStatusHistoryResponse(BaseModel):
    id: int
    old_status: Optional[str] = None
    new_status: str
    changed_by_user_id: int
    changed_at: datetime

    class Config:
        from_attributes = True

class OrderResponse(BaseModel):
    id: int
    customer_id: int
    restaurant_id: int
    rider_id: Optional[int] = None
    total_price: float
    status: OrderStatus
    payment_status: str
    delivery_address: str
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemResponse] = []

    class Config:
        from_attributes = True