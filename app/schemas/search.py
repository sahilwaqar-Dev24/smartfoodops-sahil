from typing import List, Optional
from pydantic import BaseModel


class SearchResultItem(BaseModel):
    id: int
    restaurant_id: int
    restaurant_name: str
    cuisine: Optional[str] = None
    name: str
    description: Optional[str] = None
    price: float
    similarity_score: float
    # Query ke wo lafz jo is item ke text mein mile (match ki wajah samajhne ke liye)
    matched_terms: List[str] = []


class SearchResponse(BaseModel):
    query: str
    max_price: Optional[float] = None
    cuisine: Optional[str] = None
    count: int
    results: List[SearchResultItem]