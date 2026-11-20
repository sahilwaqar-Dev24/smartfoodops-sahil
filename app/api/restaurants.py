from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.restaurant import (
    RestaurantCreate, RestaurantUpdate, RestaurantResponse,
    MenuCategoryCreate, MenuCategoryUpdate, MenuCategoryResponse,
    MenuItemCreate, MenuItemUpdate, MenuItemResponse
)
from app.api.deps import require_restaurant_admin
from app.services import restaurant_service

router = APIRouter(prefix="/restaurants", tags=["Restaurants & Menus"])


# --- Restaurant Endpoints ---

@router.post("/", response_model=RestaurantResponse, status_code=status.HTTP_201_CREATED)
def create_restaurant(
    restaurant_in: RestaurantCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_restaurant_admin)
):
    return restaurant_service.create_restaurant(db, restaurant_in, current_user)


@router.get("/", response_model=List[RestaurantResponse])
def list_restaurants(
    name: Optional[str] = Query(None, description="Search by restaurant name"),
    cuisine: Optional[str] = Query(None, description="Filter by cuisine"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    return restaurant_service.list_open_restaurants(db, name=name, cuisine=cuisine, limit=limit, offset=offset)


# NOTE: "/mine" ko "/{restaurant_id}" se pehle rakhna zaroori hai
@router.get("/mine", response_model=List[RestaurantResponse])
def list_my_restaurants(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_restaurant_admin)
):
    return restaurant_service.list_owned_restaurants(db, current_user)


@router.get("/{restaurant_id}", response_model=RestaurantResponse)
def get_restaurant(restaurant_id: int, db: Session = Depends(get_db)):
    return restaurant_service.get_restaurant(db, restaurant_id)


@router.patch("/{restaurant_id}", response_model=RestaurantResponse)
def update_restaurant(
    restaurant_id: int,
    restaurant_in: RestaurantUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_restaurant_admin)
):
    return restaurant_service.update_restaurant(db, restaurant_id, restaurant_in, current_user)


# --- Menu Category Endpoints ---

@router.post("/{restaurant_id}/categories", response_model=MenuCategoryResponse, status_code=status.HTTP_201_CREATED)
def add_category(
    restaurant_id: int,
    category_in: MenuCategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_restaurant_admin)
):
    return restaurant_service.add_category(db, restaurant_id, category_in, current_user)


@router.get("/{restaurant_id}/categories", response_model=List[MenuCategoryResponse])
def list_categories(restaurant_id: int, db: Session = Depends(get_db)):
    return restaurant_service.list_categories(db, restaurant_id)


@router.patch("/categories/{category_id}", response_model=MenuCategoryResponse)
def update_category(
    category_id: int,
    category_in: MenuCategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_restaurant_admin)
):
    return restaurant_service.update_category(db, category_id, category_in, current_user)


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_restaurant_admin)
):
    restaurant_service.delete_category(db, category_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Menu Item Endpoints ---

@router.post("/categories/{category_id}/items", response_model=MenuItemResponse, status_code=status.HTTP_201_CREATED)
def add_menu_item(
    category_id: int,
    item_in: MenuItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_restaurant_admin)
):
    return restaurant_service.add_menu_item(db, category_id, item_in, current_user)


@router.get("/categories/{category_id}/items", response_model=List[MenuItemResponse])
def list_menu_items(category_id: int, db: Session = Depends(get_db)):
    return restaurant_service.list_available_items(db, category_id)


@router.get("/categories/{category_id}/all-items", response_model=List[MenuItemResponse])
def list_all_menu_items_for_owner(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_restaurant_admin)
):
    return restaurant_service.list_all_items_for_owner(db, category_id, current_user)


@router.patch("/items/{item_id}", response_model=MenuItemResponse)
def update_menu_item(
    item_id: int,
    item_in: MenuItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_restaurant_admin)
):
    return restaurant_service.update_menu_item(db, item_id, item_in, current_user)


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_menu_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_restaurant_admin)
):
    restaurant_service.delete_menu_item(db, item_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)