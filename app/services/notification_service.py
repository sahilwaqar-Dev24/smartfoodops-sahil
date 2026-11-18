import logging
from typing import Optional
from sqlalchemy.orm import Session
from app.models.notification import Notification

logger = logging.getLogger("smartfoodops.notifications")


def create_notification(db: Session, user_id: int, message: str, order_id: Optional[int] = None) -> None:
    """Notification row add karta hai. Commit caller karega (usi request ke saath)."""
    db.add(Notification(user_id=user_id, order_id=order_id, message=message))
    logger.info("notification user_id=%s order_id=%s message=%s", user_id, order_id, message)