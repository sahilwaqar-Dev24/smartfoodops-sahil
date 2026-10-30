from typing import List, Optional
from pydantic import BaseModel
from app.schemas.analytics import SearchResultItem


class AssistantQueryRequest(BaseModel):
    question: str
    max_price: Optional[float] = None


class AssistantRecommendResponse(BaseModel):
    question: str
    reply: str
    recommended_items: List[SearchResultItem]