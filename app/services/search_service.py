"""
Simple "intelligent" search (retrieval) over menu items.

Retrieval ka matlab: user ke sawal ke liye database se sab se munasib menu items dhoondna.
Tareeqa: har item ka text (naam + description + category + cuisine) banao, TF-IDF se
numbers mein badlo, aur cosine similarity se query ke sath match karo.
"""
import logging
import re
from typing import List, Optional, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.restaurant import MenuCategory, MenuItem, Restaurant

logger = logging.getLogger("smartfoodops.search")

MIN_SCORE = 0.05  # isse kam score wale items "match" nahi maane jate

# "under 500", "below rs 300", "less than 10", "within pkr 250"
PRICE_PATTERN = re.compile(
    r"\b(?:under|below|less than|within|upto|up to)\s*(?:rs\.?|pkr)?\s*(\d+(?:\.\d+)?)",
    re.IGNORECASE,
)


def extract_price_from_query(query: str) -> Tuple[str, Optional[float]]:
    """'spicy chicken under 500' -> ('spicy chicken', 500.0)"""
    match = PRICE_PATTERN.search(query)
    if not match:
        return query, None
    price = float(match.group(1))
    cleaned = PRICE_PATTERN.sub(" ", query).strip()
    return cleaned, price


def build_search_text(item: MenuItem) -> str:
    """Searchable text: item ka naam, description, category aur restaurant ki cuisine."""
    category = item.category
    restaurant = category.restaurant if category else None
    parts = [
        item.name,
        item.description or "",
        category.name if category else "",
        restaurant.cuisine if restaurant and restaurant.cuisine else "",
    ]
    return " ".join(part for part in parts if part).strip()


def _matched_terms(query_terms: List[str], text: str) -> List[str]:
    words = set(re.findall(r"[a-z0-9]+", text.lower()))
    return [term for term in query_terms if term in words]


def search_menu_items(
    db: Session,
    query: str,
    max_price: Optional[float] = None,
    cuisine: Optional[str] = None,
    top_k: int = 5,
) -> List[dict]:
    query = (query or "").strip()
    if not query:
        return []

    # Query mein "under 500" likha ho to usko price filter bana do
    query, price_from_query = extract_price_from_query(query)
    if max_price is None:
        max_price = price_from_query
    if not query:
        return []

    # Sirf khule restaurants ke available items search honge
    items_query = (
        db.query(MenuItem)
        .join(MenuCategory, MenuItem.category_id == MenuCategory.id)
        .join(Restaurant, MenuCategory.restaurant_id == Restaurant.id)
        .filter(MenuItem.is_available == True, Restaurant.is_open == True)
    )
    if max_price is not None:
        items_query = items_query.filter(MenuItem.price <= max_price)
    if cuisine:
        items_query = items_query.filter(func.lower(Restaurant.cuisine) == cuisine.lower())

    items = items_query.order_by(MenuItem.id).all()
    if not items:
        return []

    documents = [build_search_text(item) for item in items]

    try:
        vectorizer = TfidfVectorizer(stop_words="english")
        tfidf_matrix = vectorizer.fit_transform(documents)
    except ValueError:
        # Documents mein koi kaam ka lafz nahi (sirf stop words)
        return []
    query_vector = vectorizer.transform([query])
    scores = cosine_similarity(query_vector, tfidf_matrix).flatten()

    query_terms = re.findall(r"[a-z0-9]+", query.lower())
    results = []
    for item, score in zip(items, scores):
        if score < MIN_SCORE:
            continue
        restaurant = item.category.restaurant
        results.append({
            "id": item.id,
            "restaurant_id": restaurant.id,
            "restaurant_name": restaurant.name,
            "cuisine": restaurant.cuisine,
            "name": item.name,
            "description": item.description,
            "price": item.price,
            "similarity_score": round(float(score), 4),
            "matched_terms": _matched_terms(query_terms, build_search_text(item)),
        })

    # Score ke hisaab se ranking (barabar score par sasta pehle)
    results.sort(key=lambda r: (-r["similarity_score"], r["price"]))
    logger.info("search query=%r max_price=%s cuisine=%s results=%d", query, max_price, cuisine, len(results))
    return results[:top_k]