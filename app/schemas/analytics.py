from datetime import date
from typing import List, Optional
from pydantic import BaseModel


class RestaurantOrderCount(BaseModel):
    restaurant_id: int
    restaurant_name: str
    total_orders: int
    completed_orders: int
    cancelled_orders: int


class AnalyticsSummaryResponse(BaseModel):
    total_orders: int
    completed_orders: int
    cancelled_orders: int
    rejected_orders: int
    total_revenue: float
    average_order_value: float
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    orders_per_restaurant: List[RestaurantOrderCount]