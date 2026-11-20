"""Search (TF-IDF retrieval) and the rule-based food assistant."""
from tests.helpers import create_category, create_item, create_restaurant, create_user


def _menu(client):
    admin1 = create_user(client, "kfc@test.com", "restaurant_admin")
    admin2 = create_user(client, "desi@test.com", "restaurant_admin")
    kfc = create_restaurant(client, admin1, "KFC", "Fast Food")
    desi = create_restaurant(client, admin2, "Desi Kitchen", "Desi")
    closed = create_restaurant(client, admin2, "Closed Kebab", "Desi", is_open=False)
    c1, c2, c3 = (create_category(client, admin1, kfc, "Burgers"),
                  create_category(client, admin2, desi, "Rice"),
                  create_category(client, admin2, closed, "Kebabs"))
    create_item(client, admin1, c1, "Zinger Burger", 550, description="Crispy fried chicken burger with mayo")
    create_item(client, admin1, c1, "Spicy Wings Burger", 650, description="Hot and spicy chicken wings burger")
    create_item(client, admin1, c1, "Old Twister", 400, description="spicy wrap", is_available=False)
    create_item(client, admin1, c1, "Fries", 250, description="Golden salted fries")
    create_item(client, admin2, c2, "Chicken Biryani", 450, description="Spicy chicken biryani with raita")
    create_item(client, admin2, c3, "Chapli Kebab", 350, description="spicy beef chapli kebab")


def _search(client, **params):
    res = client.get("/search/menu-items", params=params)
    assert res.status_code == 200
    return res.json()


def _names(data):
    return [r["name"] for r in data["results"]]


def test_results_are_ranked_by_relevance(client):
    _menu(client)
    data = _search(client, q="spicy chicken")
    scores = [r["similarity_score"] for r in data["results"]]
    assert scores == sorted(scores, reverse=True)
    assert scores[0] > scores[-1]
    assert data["count"] == len(data["results"])
    assert _names(data)[0] in ("Chicken Biryani", "Spicy Wings Burger")


def test_result_explains_why_it_matched(client):
    _menu(client)
    top = _search(client, q="spicy chicken")["results"][0]
    assert top["restaurant_name"] in ("Desi Kitchen", "KFC")
    assert top["price"] > 0 and top["similarity_score"] > 0
    assert set(top["matched_terms"]) == {"spicy", "chicken"}


def test_no_match_returns_empty_list(client):
    _menu(client)
    data = _search(client, q="sushi")
    assert data["count"] == 0 and data["results"] == []


def test_max_price_filter(client):
    _menu(client)
    data = _search(client, q="spicy chicken", max_price=500)
    assert _names(data) == ["Chicken Biryani"]


def test_price_can_be_written_inside_the_query(client):
    _menu(client)
    assert _names(_search(client, q="spicy chicken under 500")) == ["Chicken Biryani"]


def test_cuisine_filter(client):
    _menu(client)
    data = _search(client, q="spicy", cuisine="desi")
    assert _names(data) == ["Chicken Biryani"]


def test_closed_restaurants_and_unavailable_items_are_not_searchable(client):
    _menu(client)
    assert _search(client, q="kebab")["results"] == []     # restaurant band hai
    assert _search(client, q="twister")["results"] == []   # item unavailable hai


def test_top_k_limits_results_and_empty_query_is_invalid(client):
    _menu(client)
    assert len(_search(client, q="chicken", top_k=1)["results"]) == 1
    assert client.get("/search/menu-items", params={"q": ""}).status_code == 422
    assert _search(client, q="the and")["results"] == []   # sirf stop words


def test_assistant_recommends_real_menu_items(client):
    _menu(client)
    res = client.post("/assistant/recommend", json={"question": "I want a spicy chicken burger"})
    assert res.status_code == 200
    data = res.json()
    names = [i["name"] for i in data["recommended_items"]]
    assert names, "kam az kam ek recommendation honi chahiye"
    assert names[0] in data["reply"]
    assert all(n in ("Zinger Burger", "Spicy Wings Burger", "Chicken Biryani", "Fries") for n in names)


def test_assistant_uses_the_same_retrieval_as_search(client):
    _menu(client)
    search_names = _names(_search(client, q="spicy chicken", top_k=3))
    res = client.post("/assistant/recommend", json={"question": "spicy chicken"}).json()
    assert [i["name"] for i in res["recommended_items"]] == search_names


def test_assistant_handles_no_result_politely(client):
    _menu(client)
    res = client.post("/assistant/recommend", json={"question": "sushi rolls", "max_price": 500})
    assert res.status_code == 200
    data = res.json()
    assert data["recommended_items"] == []
    assert "couldn't find any menu items" in data["reply"]


def test_assistant_rejects_invalid_filters(client):
    _menu(client)
    assert client.post("/assistant/recommend", json={"question": "burger", "max_price": -5}).status_code == 422
    assert client.post("/assistant/recommend", json={"question": ""}).status_code == 422


def test_assistant_respects_cuisine_filter(client):
    _menu(client)
    res = client.post("/assistant/recommend", json={"question": "spicy", "cuisine": "Desi"}).json()
    assert [i["name"] for i in res["recommended_items"]] == ["Chicken Biryani"]