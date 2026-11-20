from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    order_id: Optional[int] = None
    message: str
    created_at: datetime

    class Config:
        from_attributes = True