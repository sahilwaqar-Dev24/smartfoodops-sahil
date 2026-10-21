from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# --- Restaurant Schemas ---
class RestaurantBase(BaseModel):
    name: str
    description: Optional[str] = None
    cuisine: Optional[str] = None
    address: str
    is_open: Optional[bool] = True

class RestaurantCreate(RestaurantBase):
    pass

class RestaurantUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    cuisine: Optional[str] = None
    address: Optional[str] = None
    is_open: Optional[bool] = None

class RestaurantResponse(RestaurantBase):
    id: int
    owner_user_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# --- Menu Category Schemas ---
class MenuCategoryBase(BaseModel):
    name: str
    order_index: Optional[int] = 0

class MenuCategoryCreate(MenuCategoryBase):
    pass

class MenuCategoryResponse(MenuCategoryBase):
    id: int
    restaurant_id: int

    class Config:
        from_attributes = True


# --- Menu Item Schemas ---
class MenuItemBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    is_available: Optional[bool] = True
    stock: Optional[int] = 100

class MenuItemCreate(MenuItemBase):
    pass

class MenuItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    is_available: Optional[bool] = None
    stock: Optional[int] = None

class MenuItemResponse(MenuItemBase):
    id: int
    category_id: int
    created_at: datetime

    class Config:
        from_attributes = True