from datetime import date, datetime, time, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, case, func
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.models.order import Order, OrderStatus
from app.models.restaurant import MenuItem, Restaurant
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


def search_menu_items_tfidf(
    db: Session,
    query: str,
    max_price: Optional[float] = None,
    top_k: int = 5,
):
    items_query = db.query(MenuItem).filter(MenuItem.is_available == True)
    if max_price is not None:
        items_query = items_query.filter(MenuItem.price <= max_price)

    items = items_query.all()
    if not items or not query.strip():
        return []

    # Documents corpus (Name + Description)
    documents = [
        f"{item.name} {item.description or ''}".strip()
        for item in items
    ]

    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform(documents)
    query_vector = vectorizer.transform([query])

    # Cosine Similarity calculation
    similarity = cosine_similarity(query_vector, tfidf_matrix).flatten()

    scored_items = []
    for idx, score in enumerate(similarity):
        if score > 0.05:  # relevance threshold
            item = items[idx]
            restaurant_name = (
                item.category.restaurant.name
                if item.category and item.category.restaurant
                else "Unknown"
            )
            restaurant_id = (
                item.category.restaurant_id if item.category else 0
            )

            scored_items.append({
                "id": item.id,
                "restaurant_id": restaurant_id,
                "restaurant_name": restaurant_name,
                "name": item.name,
                "description": item.description,
                "price": item.price,
                "similarity_score": round(float(score), 4),
            })

    scored_items.sort(key=lambda x: x["similarity_score"], reverse=True)
    return scored_items[:top_k]