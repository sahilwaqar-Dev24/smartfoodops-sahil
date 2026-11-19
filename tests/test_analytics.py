"""Analytics: counts, average, orders per restaurant, date filters, access control."""
from datetime import datetime

from app.models.order import Order
from tests.helpers import (create_category, create_item, create_restaurant, create_user,
                           make_ready, place_order, set_status)


def _world(client, db_session):
    """
    Admin1 ke 2 restaurants (R1, R1b), Admin2 ka 1 (R2).
    R1:  o1 DELIVERED (100), o2 CANCELLED (300), o3 REJECTED (200)
    R1b: o4 PLACED (100) -> 15 Jan 2026 ki date par
    R2:  o5 PLACED (500)
    """
    w = {}
    w["admin1"] = create_user(client, "admin1@test.com", "restaurant_admin")
    w["admin2"] = create_user(client, "admin2@test.com", "restaurant_admin")
    w["customer"] = create_user(client, "cust@test.com", "customer")
    w["rider"] = create_user(client, "rider@test.com", "rider")

    def make_restaurant(admin, name):
        rid = create_restaurant(client, admin, name)
        item = create_item(client, admin, create_category(client, admin, rid), price=100.0, stock=100)
        return rid, item

    w["r1"], i1 = make_restaurant(w["admin1"], "R1")
    w["r1b"], i1b = make_restaurant(w["admin1"], "R1 Branch")
    w["r2"], i2 = make_restaurant(w["admin2"], "R2")

    o1 = place_order(client, w["customer"], w["r1"], [(i1, 1)]).json()["id"]
    o2 = place_order(client, w["customer"], w["r1"], [(i1, 3)]).json()["id"]
    o3 = place_order(client, w["customer"], w["r1"], [(i1, 2)]).json()["id"]
    o4 = place_order(client, w["customer"], w["r1b"], [(i1b, 1)]).json()["id"]
    place_order(client, w["customer"], w["r2"], [(i2, 5)])

    make_ready(client, w["admin1"], o1)
    client.post(f"/orders/{o1}/assign-rider", headers=w["admin1"])
    set_status(client, w["rider"], o1, "PICKED_UP")
    set_status(client, w["rider"], o1, "DELIVERED")
    set_status(client, w["customer"], o2, "CANCELLED")
    client.post(f"/orders/{o3}/reject", headers=w["admin1"])

    db_session.query(Order).filter(Order.id == o4).update({"created_at": datetime(2026, 1, 15, 10, 0)})
    db_session.commit()
    return w


def test_analytics_numbers_match_the_data(client, db_session):
    w = _world(client, db_session)
    data = client.get("/analytics/platform", headers=w["admin1"]).json()
    assert data["total_orders"] == 4
    assert data["completed_orders"] == 1
    assert data["cancelled_orders"] == 1
    assert data["rejected_orders"] == 1
    assert data["total_revenue"] == 100.0                       # sirf DELIVERED
    assert data["average_order_value"] == 175.0                 # (100+300+200+100)/4


def test_orders_per_restaurant(client, db_session):
    w = _world(client, db_session)
    rows = client.get("/analytics/orders-per-restaurant", headers=w["admin1"]).json()
    by_name = {r["restaurant_name"]: r for r in rows}
    assert by_name["R1"]["total_orders"] == 3
    assert by_name["R1"]["completed_orders"] == 1
    assert by_name["R1"]["cancelled_orders"] == 1
    assert by_name["R1 Branch"]["total_orders"] == 1
    assert "R2" not in by_name   # dusre admin ka restaurant nahi dikhta


def test_date_filters(client, db_session):
    w = _world(client, db_session)
    jan15 = client.get("/analytics/platform?date_from=2026-01-15&date_to=2026-01-15", headers=w["admin1"]).json()
    assert jan15["total_orders"] == 1                           # date_to inclusive
    until_jan31 = client.get("/analytics/platform?date_to=2026-01-31", headers=w["admin1"]).json()
    assert until_jan31["total_orders"] == 1
    future = client.get("/analytics/platform?date_from=2999-01-01", headers=w["admin1"]).json()
    assert future["total_orders"] == 0 and future["average_order_value"] == 0
    today = datetime.utcnow().date().isoformat()
    today_only = client.get(f"/analytics/platform?date_from={today}&date_to={today}", headers=w["admin1"]).json()
    assert today_only["total_orders"] == 3


def test_invalid_date_range_is_rejected(client, db_session):
    w = _world(client, db_session)
    res = client.get("/analytics/platform?date_from=2026-05-01&date_to=2026-01-01", headers=w["admin1"])
    assert res.status_code == 400
    assert client.get("/analytics/platform?date_from=not-a-date", headers=w["admin1"]).status_code == 422


def test_admin_cannot_see_other_admins_analytics(client, db_session):
    w = _world(client, db_session)
    other = client.get("/analytics/platform", headers=w["admin2"]).json()
    assert other["total_orders"] == 1
    assert client.get(f"/analytics/restaurants/{w['r1']}", headers=w["admin2"]).status_code == 403
    assert client.get("/analytics/restaurants/99999", headers=w["admin1"]).status_code == 404


def test_single_restaurant_analytics(client, db_session):
    w = _world(client, db_session)
    data = client.get(f"/analytics/restaurants/{w['r1']}", headers=w["admin1"]).json()
    assert data["total_orders"] == 3
    assert len(data["orders_per_restaurant"]) == 1


def test_customer_and_rider_cannot_view_analytics(client, db_session):
    w = _world(client, db_session)
    assert client.get("/analytics/platform", headers=w["customer"]).status_code == 403
    assert client.get("/analytics/orders-per-restaurant", headers=w["rider"]).status_code == 403
    assert client.get("/analytics/platform").status_code == 401


def test_admin_without_restaurants_gets_zeroes(client):
    admin = create_user(client, "new@test.com", "restaurant_admin")
    data = client.get("/analytics/platform", headers=admin).json()
    assert data["total_orders"] == 0
    assert data["orders_per_restaurant"] == []