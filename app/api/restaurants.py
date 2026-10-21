from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.models.user import User
from app.models.restaurant import Restaurant, MenuCategory, MenuItem
from app.schemas.restaurant import (
    RestaurantCreate, RestaurantUpdate, RestaurantResponse,
    MenuCategoryCreate, MenuCategoryResponse,
    MenuItemCreate, MenuItemUpdate, MenuItemResponse
)
from app.api.deps import get_current_user, require_restaurant_admin

router = APIRouter(prefix="/restaurants", tags=["Restaurants & Menus"])


# --- Restaurant Endpoints ---

@router.post("/", response_model=RestaurantResponse, status_code=status.HTTP_201_CREATED)
def create_restaurant(
    restaurant_in: RestaurantCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_restaurant_admin)
):
    restaurant = Restaurant(
        owner_user_id=current_user.id,
        name=restaurant_in.name,
        description=restaurant_in.description,
        cuisine=restaurant_in.cuisine,
        address=restaurant_in.address,
        is_open=restaurant_in.is_open if restaurant_in.is_open is not None else True
    )
    db.add(restaurant)
    db.commit()
    db.refresh(restaurant)
    return restaurant


@router.get("/", response_model=List[RestaurantResponse])
def list_restaurants(db: Session = Depends(get_db)):
    return db.query(Restaurant).filter(Restaurant.is_open == True).all()


@router.get("/{restaurant_id}", response_model=RestaurantResponse)
def get_restaurant(restaurant_id: int, db: Session = Depends(get_db)):
    restaurant = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
    if not restaurant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found")
    return restaurant


@router.patch("/{restaurant_id}", response_model=RestaurantResponse)
def update_restaurant(
    restaurant_id: int,
    restaurant_in: RestaurantUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_restaurant_admin)
):
    restaurant = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
    if not restaurant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found")
    if restaurant.owner_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to edit this restaurant")

    update_data = restaurant_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(restaurant, field, value)

    db.add(restaurant)
    db.commit()
    db.refresh(restaurant)
    return restaurant


# --- Menu Category Endpoints ---

@router.post("/{restaurant_id}/categories", response_model=MenuCategoryResponse, status_code=status.HTTP_201_CREATED)
def add_category(
    restaurant_id: int,
    category_in: MenuCategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_restaurant_admin)
):
    restaurant = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
    if not restaurant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found")
    if restaurant.owner_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to manage this restaurant")

    category = MenuCategory(
        restaurant_id=restaurant_id,
        name=category_in.name,
        order_index=category_in.order_index or 0
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.get("/{restaurant_id}/categories", response_model=List[MenuCategoryResponse])
def list_categories(restaurant_id: int, db: Session = Depends(get_db)):
    return db.query(MenuCategory).filter(MenuCategory.restaurant_id == restaurant_id).order_by(MenuCategory.order_index).all()


# --- Menu Item Endpoints ---

@router.post("/categories/{category_id}/items", response_model=MenuItemResponse, status_code=status.HTTP_201_CREATED)
def add_menu_item(
    category_id: int,
    item_in: MenuItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_restaurant_admin)
):
    category = db.query(MenuCategory).filter(MenuCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    restaurant = db.query(Restaurant).filter(Restaurant.id == category.restaurant_id).first()
    if restaurant.owner_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to manage this restaurant's menu")

    menu_item = MenuItem(
        category_id=category_id,
        name=item_in.name,
        description=item_in.description,
        price=item_in.price,
        is_available=item_in.is_available if item_in.is_available is not None else True,
        stock=item_in.stock if item_in.stock is not None else 100
    )
    db.add(menu_item)
    db.commit()
    db.refresh(menu_item)
    return menu_item


@router.get("/categories/{category_id}/items", response_model=List[MenuItemResponse])
def list_menu_items(category_id: int, db: Session = Depends(get_db)):
    return db.query(MenuItem).filter(MenuItem.category_id == category_id, MenuItem.is_available == True).all()


@router.patch("/items/{item_id}", response_model=MenuItemResponse)
def update_menu_item(
    item_id: int,
    item_in: MenuItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_restaurant_admin)
):
    menu_item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if not menu_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found")

    category = db.query(MenuCategory).filter(MenuCategory.id == menu_item.category_id).first()
    restaurant = db.query(Restaurant).filter(Restaurant.id == category.restaurant_id).first()
    if restaurant.owner_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to edit this item")

    update_data = item_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(menu_item, field, value)

    db.add(menu_item)
    db.commit()
    db.refresh(menu_item)
    return menu_item