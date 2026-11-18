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


class SearchResultItem(BaseModel):
    id: int
    restaurant_id: int
    restaurant_name: str
    name: str
    description: Optional[str] = None
    price: float
    similarity_score: float

    class Config:
        from_attributes = True


class SearchResponse(BaseModel):
    query: str
    count: int
    results: List[SearchResultItem]