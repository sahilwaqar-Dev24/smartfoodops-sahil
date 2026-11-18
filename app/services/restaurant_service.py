import logging
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.order import OrderItem
from app.models.restaurant import Restaurant, MenuCategory, MenuItem
from app.models.user import User
from app.schemas.restaurant import (
    RestaurantCreate, RestaurantUpdate,
    MenuCategoryCreate, MenuCategoryUpdate,
    MenuItemCreate, MenuItemUpdate,
)

logger = logging.getLogger("smartfoodops.restaurants")


# ---------- Helpers (ownership checks) ----------

def _get_restaurant_or_404(db: Session, restaurant_id: int) -> Restaurant:
    restaurant = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
    if not restaurant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found")
    return restaurant


def get_owned_restaurant(db: Session, restaurant_id: int, user: User) -> Restaurant:
    restaurant = _get_restaurant_or_404(db, restaurant_id)
    if restaurant.owner_user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage this restaurant"
        )
    return restaurant


def _get_owned_category(db: Session, category_id: int, user: User) -> MenuCategory:
    category = db.query(MenuCategory).filter(MenuCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    get_owned_restaurant(db, category.restaurant_id, user)
    return category


def _get_owned_item(db: Session, item_id: int, user: User) -> MenuItem:
    item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found")
    get_owned_restaurant(db, item.category.restaurant_id, user)
    return item


# ---------- Restaurants ----------

def create_restaurant(db: Session, data: RestaurantCreate, owner: User) -> Restaurant:
    restaurant = Restaurant(
        owner_user_id=owner.id,
        name=data.name,
        description=data.description,
        cuisine=data.cuisine,
        address=data.address,
        is_open=data.is_open if data.is_open is not None else True,
    )
    db.add(restaurant)
    db.commit()
    db.refresh(restaurant)
    logger.info("restaurant_created restaurant_id=%s owner_id=%s", restaurant.id, owner.id)
    return restaurant


def list_open_restaurants(
    db: Session,
    name: Optional[str] = None,
    cuisine: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> List[Restaurant]:
    query = db.query(Restaurant).filter(Restaurant.is_open == True)
    if name:
        query = query.filter(Restaurant.name.ilike(f"%{name}%"))
    if cuisine:
        query = query.filter(func.lower(Restaurant.cuisine) == cuisine.lower())
    return query.order_by(Restaurant.id).offset(offset).limit(limit).all()


def list_owned_restaurants(db: Session, owner: User) -> List[Restaurant]:
    return (
        db.query(Restaurant)
        .filter(Restaurant.owner_user_id == owner.id)
        .order_by(Restaurant.id)
        .all()
    )


def get_restaurant(db: Session, restaurant_id: int) -> Restaurant:
    return _get_restaurant_or_404(db, restaurant_id)


def update_restaurant(db: Session, restaurant_id: int, data: RestaurantUpdate, user: User) -> Restaurant:
    restaurant = get_owned_restaurant(db, restaurant_id, user)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(restaurant, field, value)
    db.commit()
    db.refresh(restaurant)
    logger.info("restaurant_updated restaurant_id=%s user_id=%s", restaurant.id, user.id)
    return restaurant


# ---------- Categories ----------

def add_category(db: Session, restaurant_id: int, data: MenuCategoryCreate, user: User) -> MenuCategory:
    get_owned_restaurant(db, restaurant_id, user)
    category = MenuCategory(
        restaurant_id=restaurant_id,
        name=data.name,
        order_index=data.order_index or 0,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    logger.info("category_created category_id=%s restaurant_id=%s user_id=%s", category.id, restaurant_id, user.id)
    return category


def list_categories(db: Session, restaurant_id: int) -> List[MenuCategory]:
    _get_restaurant_or_404(db, restaurant_id)
    return (
        db.query(MenuCategory)
        .filter(MenuCategory.restaurant_id == restaurant_id)
        .order_by(MenuCategory.order_index, MenuCategory.id)
        .all()
    )


def update_category(db: Session, category_id: int, data: MenuCategoryUpdate, user: User) -> MenuCategory:
    category = _get_owned_category(db, category_id, user)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    db.commit()
    db.refresh(category)
    logger.info("category_updated category_id=%s user_id=%s", category.id, user.id)
    return category


def delete_category(db: Session, category_id: int, user: User) -> None:
    category = _get_owned_category(db, category_id, user)

    # Purane orders ka record na bigde: agar kisi item ka order ho chuka hai to delete nahi
    item_ids = [item.id for item in category.items]
    if item_ids:
        used = db.query(func.count(OrderItem.id)).filter(OrderItem.menu_item_id.in_(item_ids)).scalar()
        if used:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This category has items that appear in past orders. Mark those items unavailable instead of deleting"
            )

    db.delete(category)
    db.commit()
    logger.info("category_deleted category_id=%s user_id=%s", category_id, user.id)


# ---------- Menu items ----------

def add_menu_item(db: Session, category_id: int, data: MenuItemCreate, user: User) -> MenuItem:
    _get_owned_category(db, category_id, user)
    item = MenuItem(
        category_id=category_id,
        name=data.name,
        description=data.description,
        price=data.price,
        is_available=data.is_available if data.is_available is not None else True,
        stock=data.stock if data.stock is not None else 100,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    logger.info("menu_item_created item_id=%s category_id=%s user_id=%s", item.id, category_id, user.id)
    return item


def list_available_items(db: Session, category_id: int) -> List[MenuItem]:
    """Customers ke liye: sirf available items."""
    category = db.query(MenuCategory).filter(MenuCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return (
        db.query(MenuItem)
        .filter(MenuItem.category_id == category_id, MenuItem.is_available == True)
        .order_by(MenuItem.id)
        .all()
    )


def list_all_items_for_owner(db: Session, category_id: int, user: User) -> List[MenuItem]:
    """Restaurant admin ke liye: apni category ke saare items (unavailable bhi)."""
    _get_owned_category(db, category_id, user)
    return db.query(MenuItem).filter(MenuItem.category_id == category_id).order_by(MenuItem.id).all()


def update_menu_item(db: Session, item_id: int, data: MenuItemUpdate, user: User) -> MenuItem:
    item = _get_owned_item(db, item_id, user)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    logger.info("menu_item_updated item_id=%s user_id=%s", item.id, user.id)
    return item


def delete_menu_item(db: Session, item_id: int, user: User) -> None:
    item = _get_owned_item(db, item_id, user)

    used = db.query(func.count(OrderItem.id)).filter(OrderItem.menu_item_id == item.id).scalar()
    if used:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This item appears in past orders and cannot be deleted. Mark it unavailable instead"
        )

    db.delete(item)
    db.commit()
    logger.info("menu_item_deleted item_id=%s user_id=%s", item_id, user.id)