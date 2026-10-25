from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from app.models.order import OrderStatus, PaymentStatus


# Customer request item (Customer sirf item_id aur quantity bhej sakta hai, unit_price server tay karega)
class OrderItemCreate(BaseModel):
    menu_item_id: int
    quantity: int = Field(gt=0, description="Quantity must be greater than zero")


# Customer order create request
class OrderCreate(BaseModel):
    restaurant_id: int
    delivery_address: str = Field(min_length=5, description="Delivery address is required")
    items: List[OrderItemCreate] = Field(min_items=1, description="Order must contain at least one item")


# Response item schema
class OrderItemResponse(BaseModel):
    id: int
    menu_item_id: int
    item_name: str
    unit_price: float
    quantity: int
    line_total: float

    class Config:
        from_attributes = True


# Status history schema
class OrderStatusHistoryResponse(BaseModel):
    id: int
    old_status: Optional[str]
    new_status: str
    changed_by_user_id: Optional[int]
    changed_at: datetime

    class Config:
        from_attributes = True


# Main Order Response schema
class OrderResponse(BaseModel):
    id: int
    customer_id: int
    restaurant_id: int
    total_price: float
    status: OrderStatus
    payment_status: PaymentStatus
    delivery_address: str
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemResponse] = []

    class Config:
        from_attributes = True


# Order status update schema (Admin/Restaurant status change karne ke liye)
class OrderStatusUpdate(BaseModel):
    status: OrderStatus