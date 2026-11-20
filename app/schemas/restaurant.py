from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# --- Restaurant Schemas ---
class RestaurantBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None
    cuisine: Optional[str] = Field(default=None, max_length=50)
    address: str = Field(min_length=1, max_length=255)
    is_open: Optional[bool] = True

class RestaurantCreate(RestaurantBase):
    pass

class RestaurantUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = None
    cuisine: Optional[str] = Field(default=None, max_length=50)
    address: Optional[str] = Field(default=None, min_length=1, max_length=255)
    is_open: Optional[bool] = None

class RestaurantResponse(RestaurantBase):
    id: int
    owner_user_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# --- Menu Category Schemas ---
class MenuCategoryBase(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    order_index: Optional[int] = 0

class MenuCategoryCreate(MenuCategoryBase):
    pass

class MenuCategoryUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    order_index: Optional[int] = None

class MenuCategoryResponse(MenuCategoryBase):
    id: int
    restaurant_id: int

    class Config:
        from_attributes = True


# --- Menu Item Schemas ---
class MenuItemBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None
    price: float = Field(gt=0, description="Price must be greater than 0")
    is_available: Optional[bool] = True
    stock: Optional[int] = Field(default=100, ge=0, description="Stock cannot be negative")

class MenuItemCreate(MenuItemBase):
    pass

class MenuItemUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = None
    price: Optional[float] = Field(default=None, gt=0)
    is_available: Optional[bool] = None
    stock: Optional[int] = Field(default=None, ge=0)

class MenuItemResponse(MenuItemBase):
    id: int
    category_id: int
    created_at: datetime

    class Config:
        from_attributes = True