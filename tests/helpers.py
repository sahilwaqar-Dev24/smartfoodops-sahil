PASSWORD = "Password123!"


def register(client, email, role, name=None):
    return client.post(
        "/auth/register",
        json={"name": name or email.split("@")[0], "email": email, "password": PASSWORD, "role": role},
    )


def login_headers(client, email):
    res = client.post("/auth/login", data={"username": email, "password": PASSWORD})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def create_user(client, email, role):
    """Register + login, headers wapas karta hai."""
    assert register(client, email, role).status_code == 201
    return login_headers(client, email)


def create_restaurant(client, headers, name="Test Restaurant", cuisine="Desi", is_open=True):
    res = client.post(
        "/restaurants/",
        json={"name": name, "address": "Mandian, Abbottabad", "cuisine": cuisine, "is_open": is_open},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


def create_category(client, headers, restaurant_id, name="Mains"):
    res = client.post(f"/restaurants/{restaurant_id}/categories", json={"name": name}, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()["id"]


def create_item(client, headers, category_id, name="Chicken Biryani", price=100.0, stock=10,
                description="Spicy chicken biryani", is_available=True):
    res = client.post(
        f"/restaurants/categories/{category_id}/items",
        json={"name": name, "price": price, "stock": stock, "description": description,
              "is_available": is_available},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


def place_order(client, headers, restaurant_id, items, **extra):
    """items = [(menu_item_id, quantity), ...]"""
    payload = {
        "restaurant_id": restaurant_id,
        "delivery_address": "House 1, Abbottabad",
        "items": [{"menu_item_id": i, "quantity": q} for i, q in items],
    }
    payload.update(extra)
    return client.post("/orders/", json=payload, headers=headers)


def set_status(client, headers, order_id, status):
    return client.patch(f"/orders/{order_id}/status", json={"status": status}, headers=headers)


def make_ready(client, admin_headers, order_id):
    for status in ["ACCEPTED", "PREPARING", "READY"]:
        assert set_status(client, admin_headers, order_id, status).status_code == 200