from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.assistant import AssistantQueryRequest, AssistantRecommendResponse
from app.services.search_service import search_menu_items

router = APIRouter(prefix="/assistant", tags=["Food Assistant"])


def build_reply(question: str, items: list, max_price=None, cuisine=None) -> str:
    """Rule-based reply: sirf retrieved items ka naam lete hain, kuch khud nahi banate."""
    if not items:
        filters = []
        if cuisine:
            filters.append(f"{cuisine} cuisine")
        if max_price:
            filters.append(f"under Rs. {max_price:g}")
        extra = f" ({', '.join(filters)})" if filters else ""
        return (
            f"Sorry, I couldn't find any menu items matching '{question}'{extra}. "
            "Try different words, for example 'burger', 'biryani' or 'fries'."
        )

    top = items[0]
    reply = (
        f"I recommend the {top['name']} from {top['restaurant_name']} "
        f"for Rs. {top['price']:.2f}."
    )
    if top.get("matched_terms"):
        reply += f" It matches your words: {', '.join(top['matched_terms'])}."
    others = items[1:]
    if others:
        names = ", ".join(f"{i['name']} ({i['restaurant_name']}, Rs. {i['price']:.2f})" for i in others)
        reply += f" Other options: {names}."
    return reply


@router.post("/recommend", response_model=AssistantRecommendResponse, summary="Simple food assistant")
def recommend_food(payload: AssistantQueryRequest, db: Session = Depends(get_db)):
    # Wahi retrieval function jo /search/menu-items use karta hai
    matched_items = search_menu_items(
        db,
        query=payload.question,
        max_price=payload.max_price,
        cuisine=payload.cuisine,
        top_k=3,
    )
    return AssistantRecommendResponse(
        question=payload.question,
        reply=build_reply(payload.question, matched_items, payload.max_price, payload.cuisine),
        recommended_items=matched_items,
    )