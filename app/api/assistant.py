from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.assistant import AssistantQueryRequest, AssistantRecommendResponse
from app.services.analytics_service import search_menu_items_tfidf

router = APIRouter(prefix="/assistant", tags=["Food Assistant"])


@router.post("/recommend", response_model=AssistantRecommendResponse, summary="Simple Food Assistant Recommendation")
def recommend_food(payload: AssistantQueryRequest, db: Session = Depends(get_db)):
    # 1. Reuse existing TF-IDF search logic
    matched_items = search_menu_items_tfidf(
        db=db,
        query=payload.question,
        max_price=payload.max_price,
        top_k=3,
    )

    # 2. Format rule-based recommendation reply without external LLM
    if not matched_items:
        reply = (
            f"I couldn't find any menu items matching '{payload.question}'"
            + (f" under Rs. {payload.max_price}" if payload.max_price else "")
            + ". Try searching for burgers, fries, or fast food!"
        )
    else:
        top_item = matched_items[0]
        reply = (
            f"Based on your search for '{payload.question}', I recommend the '{top_item['name']}' "
            f"from {top_item['restaurant_name']} for Rs. {top_item['price']:.2f}. "
            f"{top_item.get('description', '')}"
        ).strip()

    return AssistantRecommendResponse(
        question=payload.question,
        reply=reply,
        recommended_items=matched_items,
    )