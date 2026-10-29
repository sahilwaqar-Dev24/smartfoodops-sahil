from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.models.order import Order, OrderStatus
from app.models.restaurant import MenuItem, Restaurant
from app.models.user import User


def get_platform_analytics(db: Session):
    total_orders = db.query(func.count(Order.id)).scalar() or 0
    completed_orders = (
        db.query(func.count(Order.id))
        .filter(Order.status == OrderStatus.DELIVERED)
        .scalar()
        or 0
    )
    cancelled_orders = (
        db.query(func.count(Order.id))
        .filter(Order.status == OrderStatus.CANCELLED)
        .scalar()
        or 0
    )

    total_revenue = (
        db.query(func.sum(Order.total_price))
        .filter(Order.status == OrderStatus.DELIVERED)
        .scalar()
        or 0.0
    )

    avg_order_value = (
        db.query(func.avg(Order.total_price))
        .filter(Order.status == OrderStatus.DELIVERED)
        .scalar()
        or 0.0
    )

    return {
        "total_orders": total_orders,
        "completed_orders": completed_orders,
        "cancelled_orders": cancelled_orders,
        "total_revenue": round(float(total_revenue), 2),
        "average_order_value": round(float(avg_order_value), 2),
    }


def get_restaurant_analytics(db: Session, restaurant_id: int):
    total_orders = (
        db.query(func.count(Order.id))
        .filter(Order.restaurant_id == restaurant_id)
        .scalar()
        or 0
    )

    completed_orders = (
        db.query(func.count(Order.id))
        .filter(
            Order.restaurant_id == restaurant_id,
            Order.status == OrderStatus.DELIVERED,
        )
        .scalar()
        or 0
    )

    cancelled_orders = (
        db.query(func.count(Order.id))
        .filter(
            Order.restaurant_id == restaurant_id,
            Order.status == OrderStatus.CANCELLED,
        )
        .scalar()
        or 0
    )

    total_revenue = (
        db.query(func.sum(Order.total_price))
        .filter(
            Order.restaurant_id == restaurant_id,
            Order.status == OrderStatus.DELIVERED,
        )
        .scalar()
        or 0.0
    )

    avg_order_value = (
        db.query(func.avg(Order.total_price))
        .filter(
            Order.restaurant_id == restaurant_id,
            Order.status == OrderStatus.DELIVERED,
        )
        .scalar()
        or 0.0
    )

    return {
        "total_orders": total_orders,
        "completed_orders": completed_orders,
        "cancelled_orders": cancelled_orders,
        "total_revenue": round(float(total_revenue), 2),
        "average_order_value": round(float(avg_order_value), 2),
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