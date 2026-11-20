from typing import List, Optional
from pydantic import BaseModel, Field
from app.schemas.search import SearchResultItem


class AssistantQueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=300)
    max_price: Optional[float] = Field(default=None, gt=0)
    cuisine: Optional[str] = Field(default=None, max_length=50)


class AssistantRecommendResponse(BaseModel):
    question: str
    reply: str
    recommended_items: List[SearchResultItem]