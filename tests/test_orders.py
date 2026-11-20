from tests.helpers import (create_category, create_item, create_restaurant, create_user, place_order)


def _setup(client, stock=10):
    admin = create_user(client, "admin@test.com", "restaurant_admin")
    customer = create_user(client, "cust@test.com", "customer")
    rid = create_restaurant(client, admin, "Desi Kitchen")
    cat = create_category(client, admin, rid)
    biryani = create_item(client, admin, cat, "Chicken Biryani", price=450.0, stock=stock)
    fries = create_item(client, admin, cat, "Fries", price=125.5, stock=stock)
    return admin, customer, rid, cat, biryani, fries


def _stock(client, category_id, item_id):
    items = client.get(f"/restaurants/categories/{category_id}/items").json()
    return next(i["stock"] for i in items if i["id"] == item_id)


def test_server_calculates_total_from_database_prices(client):
    _, customer, rid, _, biryani, fries = _setup(client)
    res = place_order(client, customer, rid, [(biryani, 2), (fries, 3)])
    assert res.status_code == 201
    data = res.json()
    assert data["total_price"] == 2 * 450.0 + 3 * 125.5  # 1276.5
    assert data["status"] == "PLACED"
    assert data["payment_status"] == "PAID"


def test_client_cannot_send_its_own_total(client):
    _, customer, rid, _, biryani, _ = _setup(client)
    res = place_order(client, customer, rid, [(biryani, 1)], total_price=1, total=1)
    assert res.status_code == 201
    assert res.json()["total_price"] == 450.0


def test_order_items_store_price_snapshot(client):
    admin, customer, rid, _, biryani, _ = _setup(client)
    order = place_order(client, customer, rid, [(biryani, 2)]).json()
    client.patch(f"/restaurants/items/{biryani}", json={"price": 999.0}, headers=admin)  # menu price badal gayi
    old = client.get(f"/orders/{order['id']}", headers=customer).json()
    line = old["items"][0]
    assert (line["item_name"], line["unit_price"], line["quantity"], line["line_total"]) == ("Chicken Biryani", 450.0, 2, 900.0)


def test_unavailable_item_is_rejected(client):
    admin, customer, rid, cat, _, _ = _setup(client)
    hidden = create_item(client, admin, cat, "Old Dish", price=50, is_available=False)
    res = place_order(client, customer, rid, [(hidden, 1)])
    assert res.status_code == 400
    assert "unavailable" in res.json()["error"]["message"]


def test_quantity_above_stock_is_rejected(client):
    _, customer, rid, _, biryani, _ = _setup(client, stock=2)
    res = place_order(client, customer, rid, [(biryani, 5)])
    assert res.status_code == 400
    assert "stock" in res.json()["error"]["message"].lower()


def test_stock_is_reduced_after_order_and_restored_on_cancel(client):
    _, customer, rid, cat, biryani, _ = _setup(client, stock=10)
    order_id = place_order(client, customer, rid, [(biryani, 4)]).json()["id"]
    assert _stock(client, cat, biryani) == 6
    client.patch(f"/orders/{order_id}/status", json={"status": "CANCELLED"}, headers=customer)
    assert _stock(client, cat, biryani) == 10


def test_closed_restaurant_cannot_accept_orders(client):
    admin, customer, _, _, _, _ = _setup(client)
    rid = create_restaurant(client, admin, "Closed Cafe", is_open=False)
    cat = create_category(client, admin, rid)
    item = create_item(client, admin, cat)
    res = place_order(client, customer, rid, [(item, 1)])
    assert res.status_code == 400
    assert "closed" in res.json()["error"]["message"]


def test_empty_cart_is_rejected(client):
    _, customer, rid, _, _, _ = _setup(client)
    assert place_order(client, customer, rid, []).status_code == 400


def test_zero_or_negative_quantity_is_rejected(client):
    _, customer, rid, _, biryani, _ = _setup(client)
    assert place_order(client, customer, rid, [(biryani, 0)]).status_code == 422
    assert place_order(client, customer, rid, [(biryani, -3)]).status_code == 422


def test_item_from_another_restaurant_is_rejected(client):
    admin, customer, rid, _, biryani, _ = _setup(client)
    other_admin = create_user(client, "other@test.com", "restaurant_admin")
    other_rid = create_restaurant(client, other_admin, "Other")
    other_item = create_item(client, other_admin, create_category(client, other_admin, other_rid))
    assert place_order(client, customer, rid, [(other_item, 1)]).status_code == 400


def test_failed_payment_cancels_order_and_keeps_stock(client):
    _, customer, rid, cat, biryani, _ = _setup(client, stock=10)
    res = place_order(client, customer, rid, [(biryani, 3)], simulate_payment="FAILED")
    assert res.status_code == 201
    assert res.json()["payment_status"] == "FAILED"
    assert res.json()["status"] == "CANCELLED"
    assert _stock(client, cat, biryani) == 10