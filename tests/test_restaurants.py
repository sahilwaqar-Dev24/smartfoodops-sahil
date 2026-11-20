"""Restaurants and menus: browse, search, pagination, owner CRUD, delete rules."""
from tests.helpers import (create_category, create_item, create_restaurant, create_user, place_order)


def _names(response):
    return [r["name"] for r in response.json()]


def test_customers_only_see_open_restaurants(client):
    admin = create_user(client, "admin@test.com", "restaurant_admin")
    create_restaurant(client, admin, "Open Place", "Desi")
    create_restaurant(client, admin, "Closed Place", "Desi", is_open=False)
    assert _names(client.get("/restaurants/")) == ["Open Place"]


def test_search_restaurants_by_name_and_cuisine(client):
    admin = create_user(client, "admin@test.com", "restaurant_admin")
    create_restaurant(client, admin, "Pizza Hut", "Italian")
    create_restaurant(client, admin, "Pizza Point", "Italian")
    create_restaurant(client, admin, "Karahi House", "Desi")
    assert sorted(_names(client.get("/restaurants/?name=pizza"))) == ["Pizza Hut", "Pizza Point"]
    assert _names(client.get("/restaurants/?cuisine=desi")) == ["Karahi House"]
    assert client.get("/restaurants/?name=pizza&cuisine=desi").json() == []


def test_restaurant_list_pagination(client):
    admin = create_user(client, "admin@test.com", "restaurant_admin")
    for i in range(5):
        create_restaurant(client, admin, f"Restaurant {i}")
    assert len(client.get("/restaurants/?limit=2").json()) == 2
    assert _names(client.get("/restaurants/?limit=2&offset=4")) == ["Restaurant 4"]
    assert client.get("/restaurants/?limit=0").status_code == 422
    assert client.get("/restaurants/?offset=-1").status_code == 422


def test_admin_sees_own_closed_restaurant_in_mine(client):
    admin = create_user(client, "admin@test.com", "restaurant_admin")
    other = create_user(client, "other@test.com", "restaurant_admin")
    create_restaurant(client, admin, "My Closed", is_open=False)
    create_restaurant(client, other, "Not Mine")
    assert _names(client.get("/restaurants/mine", headers=admin)) == ["My Closed"]


def test_closing_a_restaurant_hides_it_from_customers(client):
    admin = create_user(client, "admin@test.com", "restaurant_admin")
    rid = create_restaurant(client, admin, "Cafe")
    assert client.patch(f"/restaurants/{rid}", json={"is_open": False}, headers=admin).json()["is_open"] is False
    assert client.get("/restaurants/").json() == []


def test_customers_see_only_available_items_but_owner_sees_all(client):
    admin = create_user(client, "admin@test.com", "restaurant_admin")
    customer = create_user(client, "cust@test.com", "customer")
    rid = create_restaurant(client, admin)
    cat = create_category(client, admin, rid)
    create_item(client, admin, cat, "Visible", price=10)
    create_item(client, admin, cat, "Hidden", price=10, is_available=False)

    public = [i["name"] for i in client.get(f"/restaurants/categories/{cat}/items").json()]
    owner = [i["name"] for i in client.get(f"/restaurants/categories/{cat}/all-items", headers=admin).json()]
    assert public == ["Visible"]
    assert owner == ["Visible", "Hidden"]
    assert client.get(f"/restaurants/categories/{cat}/all-items", headers=customer).status_code == 403


def test_menu_validation_rejects_bad_values(client):
    admin = create_user(client, "admin@test.com", "restaurant_admin")
    rid = create_restaurant(client, admin)
    cat = create_category(client, admin, rid)
    url = f"/restaurants/categories/{cat}/items"
    assert client.post(url, json={"name": "x", "price": -5}, headers=admin).status_code == 422
    assert client.post(url, json={"name": "x", "price": 0}, headers=admin).status_code == 422
    assert client.post(url, json={"name": "x", "price": 5, "stock": -1}, headers=admin).status_code == 422
    assert client.post(url, json={"name": "", "price": 5}, headers=admin).status_code == 422
    assert client.post(f"/restaurants/{rid}/categories", json={"name": ""}, headers=admin).status_code == 422


def test_owner_can_update_item_and_category(client):
    admin = create_user(client, "admin@test.com", "restaurant_admin")
    rid = create_restaurant(client, admin)
    cat = create_category(client, admin, rid, "Old Name")
    item = create_item(client, admin, cat, price=100)
    assert client.patch(f"/restaurants/items/{item}", json={"price": 150}, headers=admin).json()["price"] == 150
    assert client.patch(f"/restaurants/items/{item}", json={"price": -1}, headers=admin).status_code == 422
    assert client.patch(f"/restaurants/categories/{cat}", json={"name": "New Name"}, headers=admin).json()["name"] == "New Name"


def test_owner_can_delete_unused_item_and_category(client):
    admin = create_user(client, "admin@test.com", "restaurant_admin")
    rid = create_restaurant(client, admin)
    cat = create_category(client, admin, rid)
    item = create_item(client, admin, cat)
    assert client.delete(f"/restaurants/items/{item}", headers=admin).status_code == 204
    assert client.delete(f"/restaurants/items/{item}", headers=admin).status_code == 404
    assert client.delete(f"/restaurants/categories/{cat}", headers=admin).status_code == 204
    assert client.get(f"/restaurants/{rid}/categories").json() == []


def test_item_with_past_orders_cannot_be_deleted(client):
    admin = create_user(client, "admin@test.com", "restaurant_admin")
    customer = create_user(client, "cust@test.com", "customer")
    rid = create_restaurant(client, admin)
    cat = create_category(client, admin, rid)
    item = create_item(client, admin, cat)
    assert place_order(client, customer, rid, [(item, 1)]).status_code == 201

    res = client.delete(f"/restaurants/items/{item}", headers=admin)
    assert res.status_code == 409
    assert "unavailable" in res.json()["error"]["message"]
    assert client.delete(f"/restaurants/categories/{cat}", headers=admin).status_code == 409