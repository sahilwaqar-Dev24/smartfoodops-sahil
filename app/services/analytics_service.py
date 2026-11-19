from datetime import date, datetime, time, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, case, func

from app.models.order import Order, OrderStatus
from app.models.restaurant import Restaurant
from app.models.user import User


def get_owned_restaurant_ids(db: Session, owner: User) -> List[int]:
    rows = db.query(Restaurant.id).filter(Restaurant.owner_user_id == owner.id).all()
    return [row[0] for row in rows]


def _date_conditions(date_from: Optional[date], date_to: Optional[date]) -> list:
    """date_to inclusive hota hai: us din ke saare orders count honge."""
    conditions = []
    if date_from:
        conditions.append(Order.created_at >= datetime.combine(date_from, time.min))
    if date_to:
        conditions.append(Order.created_at < datetime.combine(date_to + timedelta(days=1), time.min))
    return conditions


def get_orders_per_restaurant(
    db: Session,
    restaurant_ids: List[int],
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> list:
    """GROUP BY query: har restaurant ke orders. Zero orders wale restaurants bhi dikhte hain."""
    rows = (
        db.query(
            Restaurant.id,
            Restaurant.name,
            func.count(Order.id),
            func.sum(case((Order.status == OrderStatus.DELIVERED, 1), else_=0)),
            func.sum(case((Order.status == OrderStatus.CANCELLED, 1), else_=0)),
        )
        .outerjoin(
            Order,
            and_(Order.restaurant_id == Restaurant.id, *_date_conditions(date_from, date_to)),
        )
        .filter(Restaurant.id.in_(restaurant_ids))
        .group_by(Restaurant.id, Restaurant.name)
        .order_by(Restaurant.id)
        .all()
    )
    return [
        {
            "restaurant_id": row[0],
            "restaurant_name": row[1],
            "total_orders": row[2] or 0,
            "completed_orders": int(row[3] or 0),
            "cancelled_orders": int(row[4] or 0),
        }
        for row in rows
    ]


def get_analytics_summary(
    db: Session,
    restaurant_ids: List[int],
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> dict:
    base = [Order.restaurant_id.in_(restaurant_ids), *_date_conditions(date_from, date_to)]

    def count_orders(*extra) -> int:
        return db.query(func.count(Order.id)).filter(*base, *extra).scalar() or 0

    total_revenue = (
        db.query(func.sum(Order.total_price))
        .filter(*base, Order.status == OrderStatus.DELIVERED)
        .scalar()
        or 0.0
    )
    # Average order value = sab orders ki total_price ka average
    average_order_value = db.query(func.avg(Order.total_price)).filter(*base).scalar() or 0.0

    return {
        "total_orders": count_orders(),
        "completed_orders": count_orders(Order.status == OrderStatus.DELIVERED),
        "cancelled_orders": count_orders(Order.status == OrderStatus.CANCELLED),
        "rejected_orders": count_orders(Order.status == OrderStatus.REJECTED),
        "total_revenue": round(float(total_revenue), 2),
        "average_order_value": round(float(average_order_value), 2),
        "date_from": date_from,
        "date_to": date_to,
        "orders_per_restaurant": get_orders_per_restaurant(db, restaurant_ids, date_from, date_to),
    }