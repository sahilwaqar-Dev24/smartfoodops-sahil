from tests.helpers import (create_category, create_item, create_restaurant, create_user, place_order)

def _world(client):
    admin1 = create_user(client, "admin1@test.com", "restaurant_admin")
    admin2 = create_user(client, "admin2@test.com", "restaurant_admin")
    customer = create_user(client, "cust@test.com", "customer")
    rider = create_user(client, "rider@test.com", "rider")
    rid = create_restaurant(client, admin1, "Restaurant One")
    cat = create_category(client, admin1, rid)
    item = create_item(client, admin1, cat)
    return admin1, admin2, customer, rider, rid, cat, item


def test_customer_cannot_create_menu_item(client):
    _, _, customer, _, _, cat, _ = _world(client)
    res = client.post(f"/restaurants/categories/{cat}/items", json={"name": "x", "price": 10}, headers=customer)
    assert res.status_code == 403


def test_rider_cannot_manage_restaurants(client):
    _, _, _, rider, rid, _, _ = _world(client)
    assert client.post("/restaurants/", json={"name": "R", "address": "A"}, headers=rider).status_code == 403
    assert client.patch(f"/restaurants/{rid}", json={"name": "Hack"}, headers=rider).status_code == 403


def test_admin_cannot_edit_another_admins_restaurant_or_menu(client):
    _, admin2, _, _, rid, cat, item = _world(client)
    assert client.patch(f"/restaurants/{rid}", json={"name": "Hacked"}, headers=admin2).status_code == 403
    assert client.post(f"/restaurants/{rid}/categories", json={"name": "x"}, headers=admin2).status_code == 403
    assert client.post(f"/restaurants/categories/{cat}/items", json={"name": "x", "price": 5}, headers=admin2).status_code == 403
    assert client.patch(f"/restaurants/items/{item}", json={"price": 1}, headers=admin2).status_code == 403
    assert client.delete(f"/restaurants/items/{item}", headers=admin2).status_code == 403


def test_only_customers_can_place_orders(client):
    admin1, _, _, rider, rid, _, item = _world(client)
    assert place_order(client, admin1, rid, [(item, 1)]).status_code == 403
    assert place_order(client, rider, rid, [(item, 1)]).status_code == 403


def test_customer_cannot_see_other_customers_order(client):
    _, _, customer, _, rid, _, item = _world(client)
    other = create_user(client, "other@test.com", "customer")
    order_id = place_order(client, customer, rid, [(item, 1)]).json()["id"]
    assert client.get(f"/orders/{order_id}", headers=other).status_code == 403
    assert client.get(f"/orders/{order_id}/history", headers=other).status_code == 403
    assert client.get("/orders/", headers=other).json() == []


def test_admin_only_sees_orders_of_own_restaurant(client):
    admin1, admin2, customer, _, rid, _, item = _world(client)
    order_id = place_order(client, customer, rid, [(item, 1)]).json()["id"]
    assert len(client.get("/orders/", headers=admin1).json()) == 1
    assert client.get("/orders/", headers=admin2).json() == []
    assert client.get(f"/orders/{order_id}", headers=admin2).status_code == 403