"""
SmartFoodOps Automated Test Suite
Covers: Health, Auth, Restaurants, Orders lifecycle, Rider RBAC, and TF-IDF Search.
"""
import pytest


# 1. Health Check Test
def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# 2. Auth: User Registration Test
def test_register_customer(client):
    payload = {
        "name": "Ali Khan",
        "email": "ali@example.com",
        "password": "Password123!",
        "role": "customer",
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "ali@example.com"
    assert data["role"] == "customer"
    assert "id" in data


# 3. Auth: Duplicate Email Registration Guard
def test_register_duplicate_email(client, seeded_users):
    payload = {
        "name": "Duplicate Admin",
        "email": "admin@test.com",
        "password": "Password123!",
        "role": "restaurant_admin",
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 400


# 4. Auth: Login Successful (Token Generation)
def test_login_success(client, seeded_users):
    response = client.post(
        "/auth/login",
        data={"username": "admin@test.com", "password": "Password123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


# 5. Auth: Login Invalid Credentials
def test_login_invalid_password(client, seeded_users):
    response = client.post(
        "/auth/login",
        data={"username": "admin@test.com", "password": "WrongPassword"},
    )
    assert response.status_code == 401


# 6. Restaurant: Public List Restaurants
def test_list_restaurants(client, seeded_restaurant):
    response = client.get("/restaurants/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["name"] == "KFC Abbottabad"


# 7. Menu: Get Items for Category
def test_get_menu_items(client, seeded_restaurant):
    category_id = seeded_restaurant["category"].id
    response = client.get(f"/restaurants/categories/{category_id}/items")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def _create_order_request(client, headers, payload):
    # Support both /orders/ and /orders endpoints based on router registration
    res = client.post("/orders/", json=payload, headers=headers)
    if res.status_code == 405 or res.status_code == 404:
        res = client.post("/orders", json=payload, headers=headers)
    if res.status_code == 405 or res.status_code == 404:
        res = client.post("/", json=payload, headers=headers)
    return res


# 8. Order: Place Order Successfully (Dynamic Price Calculation)
def test_place_order(client, seeded_restaurant, seeded_users):
    login_res = client.post(
        "/auth/login",
        data={"username": "customer@test.com", "password": "Password123!"},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    restaurant_id = seeded_restaurant["restaurant"].id
    item_id = seeded_restaurant["items"][0].id  # Zinger Burger price 550

    order_payload = {
        "restaurant_id": restaurant_id,
        "delivery_address": "Mandian, Abbottabad",
        "items": [{"menu_item_id": item_id, "quantity": 2}],
    }

    response = _create_order_request(client, headers, order_payload)
    assert response.status_code == 201
    order_data = response.json()
    assert order_data["status"] == "PLACED"
    assert order_data["total_price"] == 1100.0


# 9. Order: Invalid State Machine Transition Guard (Jump Guard)
def test_invalid_order_status_jump(client, seeded_restaurant, seeded_users):
    cust_login = client.post(
        "/auth/login",
        data={"username": "customer@test.com", "password": "Password123!"},
    )
    cust_token = cust_login.json()["access_token"]
    order_payload = {
        "restaurant_id": seeded_restaurant["restaurant"].id,
        "delivery_address": "Mandian, Abbottabad",
        "items": [{"menu_item_id": seeded_restaurant["items"][0].id, "quantity": 1}],
    }
    order_res = _create_order_request(
        client, {"Authorization": f"Bearer {cust_token}"}, order_payload
    )
    assert order_res.status_code == 201
    order_id = order_res.json()["id"]

    admin_login = client.post(
        "/auth/login",
        data={"username": "admin@test.com", "password": "Password123!"},
    )
    admin_token = admin_login.json()["access_token"]

    status_payload = {"status": "DELIVERED"}
    # Try both standard status endpoints
    invalid_res = client.patch(
        f"/orders/{order_id}/status",
        json=status_payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    if invalid_res.status_code == 404:
        invalid_res = client.patch(
            f"/{order_id}/status",
            json=status_payload,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    assert invalid_res.status_code == 409


# 10. Rider: RBAC Protection on Available Riders Endpoint
def test_rider_cannot_view_available_riders(client, seeded_users):
    rider_login = client.post(
        "/auth/login",
        data={"username": "rider@test.com", "password": "Password123!"},
    )
    token = rider_login.json()["access_token"]
    response = client.get(
        "/riders/available", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403


# 11. Search: Intelligent TF-IDF Search
def test_search_menu_items_tfidf(client, seeded_restaurant):
    response = client.get("/search/menu-items?q=burger")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] >= 1
    assert data["results"][0]["name"] == "Zinger Burger"
    assert data["results"][0]["similarity_score"] > 0


# 12. Analytics: RBAC Platform Analytics Guard
def test_analytics_rbac_guard(client, seeded_users):
    cust_login = client.post(
        "/auth/login",
        data={"username": "customer@test.com", "password": "Password123!"},
    )
    token = cust_login.json()["access_token"]
    response = client.get(
        "/analytics/platform", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403
    # 13. Assistant: Recommendation Test
def test_assistant_recommendation_success(client, seeded_restaurant):
    payload = {"question": "I want a spicy burger", "max_price": 600.0}
    response = client.post("/assistant/recommend", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["question"] == "I want a spicy burger"
    assert "Zinger Burger" in data["reply"]
    assert len(data["recommended_items"]) >= 1


# 14. Assistant: No Match Fallback
def test_assistant_no_match_fallback(client, seeded_restaurant):
    payload = {"question": "sushi rolls", "max_price": 500.0}
    response = client.post("/assistant/recommend", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "couldn't find any menu items" in data["reply"]
    assert len(data["recommended_items"]) == 0