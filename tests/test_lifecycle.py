"""Order lifecycle: status flow, 409 on invalid jumps, riders, cancel, notifications."""
from tests.helpers import (create_category, create_item, create_restaurant, create_user,
                           make_ready, place_order, set_status)


def _setup(client, with_two_riders=True):
    w = {}
    w["admin"] = create_user(client, "admin@test.com", "restaurant_admin")
    w["other_admin"] = create_user(client, "other_admin@test.com", "restaurant_admin")
    w["customer"] = create_user(client, "cust@test.com", "customer")
    w["other_customer"] = create_user(client, "cust2@test.com", "customer")
    w["rider1"] = create_user(client, "rider1@test.com", "rider")
    if with_two_riders:
        w["rider2"] = create_user(client, "rider2@test.com", "rider")
    w["rid"] = create_restaurant(client, w["admin"], "Desi Kitchen")
    w["cat"] = create_category(client, w["admin"], w["rid"])
    w["item"] = create_item(client, w["admin"], w["cat"], price=200.0, stock=20)
    return w


def _new_order(client, w, qty=1):
    res = place_order(client, w["customer"], w["rid"], [(w["item"], qty)])
    assert res.status_code == 201
    return res.json()["id"]


def _rider_available(client, headers):
    return client.get("/users/me", headers=headers).json()["is_available"]


def test_full_flow_from_placed_to_delivered(client):
    w = _setup(client)
    order_id = _new_order(client, w)
    make_ready(client, w["admin"], order_id)

    assigned = client.post(f"/orders/{order_id}/assign-rider", headers=w["admin"])
    assert assigned.status_code == 200
    assert assigned.json()["status"] == "ASSIGNED"

    assert set_status(client, w["rider1"], order_id, "PICKED_UP").json()["status"] == "PICKED_UP"
    assert set_status(client, w["rider1"], order_id, "DELIVERED").json()["status"] == "DELIVERED"

    # Customer apna final status dekh sakta hai
    orders = client.get("/orders/", headers=w["customer"]).json()
    assert [o["status"] for o in orders] == ["DELIVERED"]


def test_status_history_is_recorded_for_every_change(client):
    w = _setup(client)
    order_id = _new_order(client, w)
    make_ready(client, w["admin"], order_id)
    client.post(f"/orders/{order_id}/assign-rider", headers=w["admin"])
    set_status(client, w["rider1"], order_id, "PICKED_UP")
    set_status(client, w["rider1"], order_id, "DELIVERED")

    history = client.get(f"/orders/{order_id}/history", headers=w["customer"]).json()
    steps = [(h["old_status"], h["new_status"]) for h in history]
    assert steps == [
        (None, "PLACED"), ("PLACED", "ACCEPTED"), ("ACCEPTED", "PREPARING"), ("PREPARING", "READY"),
        ("READY", "ASSIGNED"), ("ASSIGNED", "PICKED_UP"), ("PICKED_UP", "DELIVERED"),
    ]
    assert all(h["changed_by_user_id"] for h in history)


def test_invalid_status_jumps_return_409(client):
    w = _setup(client)
    order_id = _new_order(client, w)
    assert set_status(client, w["admin"], order_id, "DELIVERED").status_code == 409
    assert set_status(client, w["admin"], order_id, "PREPARING").status_code == 409
    assert set_status(client, w["admin"], order_id, "READY").status_code == 409


def test_cannot_move_a_finished_order(client):
    w = _setup(client)
    order_id = _new_order(client, w)
    assert client.post(f"/orders/{order_id}/reject", headers=w["admin"]).status_code == 200
    assert set_status(client, w["admin"], order_id, "ACCEPTED").status_code == 409
    assert set_status(client, w["customer"], order_id, "CANCELLED").status_code == 409


def test_admin_can_reject_only_own_restaurant_order(client):
    w = _setup(client)
    order_id = _new_order(client, w)
    assert client.post(f"/orders/{order_id}/reject", headers=w["other_admin"]).status_code == 403
    assert client.post(f"/orders/{order_id}/reject", headers=w["customer"]).status_code == 403
    res = client.post(f"/orders/{order_id}/reject", headers=w["admin"])
    assert res.status_code == 200
    assert res.json()["status"] == "REJECTED"


def test_admin_can_accept_only_own_restaurant_order(client):
    w = _setup(client)
    order_id = _new_order(client, w)
    assert client.post(f"/orders/{order_id}/accept", headers=w["other_admin"]).status_code == 403
    assert client.post(f"/orders/{order_id}/accept", headers=w["admin"]).json()["status"] == "ACCEPTED"


def test_rejected_order_restores_stock(client):
    w = _setup(client)
    order_id = _new_order(client, w, qty=5)
    client.post(f"/orders/{order_id}/reject", headers=w["admin"])
    items = client.get(f"/restaurants/categories/{w['cat']}/items").json()
    assert items[0]["stock"] == 20


def test_assignment_uses_first_available_rider_and_marks_unavailable(client):
    w = _setup(client)
    order_id = _new_order(client, w)
    make_ready(client, w["admin"], order_id)
    res = client.post(f"/orders/{order_id}/assign-rider", headers=w["admin"])
    first_rider_id = client.get("/users/me", headers=w["rider1"]).json()["id"]
    assert res.json()["rider_id"] == first_rider_id
    assert _rider_available(client, w["rider1"]) is False
    assert _rider_available(client, w["rider2"]) is True


def test_rider_becomes_available_again_after_delivery(client):
    w = _setup(client, with_two_riders=False)
    order_id = _new_order(client, w)
    make_ready(client, w["admin"], order_id)
    client.post(f"/orders/{order_id}/assign-rider", headers=w["admin"])
    set_status(client, w["rider1"], order_id, "PICKED_UP")
    set_status(client, w["rider1"], order_id, "DELIVERED")
    assert _rider_available(client, w["rider1"]) is True


def test_only_assigned_rider_can_pickup_and_deliver(client):
    w = _setup(client)
    order_id = _new_order(client, w)
    make_ready(client, w["admin"], order_id)
    client.post(f"/orders/{order_id}/assign-rider", headers=w["admin"])  # rider1 ko mila

    assert set_status(client, w["rider2"], order_id, "PICKED_UP").status_code == 403
    assert set_status(client, w["customer"], order_id, "PICKED_UP").status_code == 403
    assert set_status(client, w["admin"], order_id, "PICKED_UP").status_code == 403
    assert set_status(client, w["rider1"], order_id, "PICKED_UP").status_code == 200
    assert set_status(client, w["rider2"], order_id, "DELIVERED").status_code == 403


def test_no_available_rider_keeps_order_ready_with_clear_message(client):
    w = _setup(client, with_two_riders=False)
    client.patch("/riders/me/availability", headers=w["rider1"])  # rider off-duty
    order_id = _new_order(client, w)
    make_ready(client, w["admin"], order_id)

    res = client.post(f"/orders/{order_id}/assign-rider", headers=w["admin"])
    assert res.status_code == 409
    assert "No rider is available" in res.json()["error"]["message"]
    assert client.get(f"/orders/{order_id}", headers=w["admin"]).json()["status"] == "READY"


def test_assigned_status_cannot_be_set_through_patch(client):
    w = _setup(client)
    order_id = _new_order(client, w)
    make_ready(client, w["admin"], order_id)
    assert set_status(client, w["admin"], order_id, "ASSIGNED").status_code == 400


def test_only_owner_or_restaurant_can_cancel(client):
    w = _setup(client)
    order_id = _new_order(client, w)
    assert set_status(client, w["other_customer"], order_id, "CANCELLED").status_code == 403
    assert set_status(client, w["other_admin"], order_id, "CANCELLED").status_code == 403
    assert set_status(client, w["rider1"], order_id, "CANCELLED").status_code == 403
    assert set_status(client, w["customer"], order_id, "CANCELLED").json()["status"] == "CANCELLED"


def test_cancel_after_assignment_frees_the_rider(client):
    w = _setup(client)
    order_id = _new_order(client, w)
    make_ready(client, w["admin"], order_id)
    client.post(f"/orders/{order_id}/assign-rider", headers=w["admin"])
    assert _rider_available(client, w["rider1"]) is False
    assert set_status(client, w["customer"], order_id, "CANCELLED").status_code == 200
    assert _rider_available(client, w["rider1"]) is True


def test_cannot_cancel_after_pickup(client):
    w = _setup(client)
    order_id = _new_order(client, w)
    make_ready(client, w["admin"], order_id)
    client.post(f"/orders/{order_id}/assign-rider", headers=w["admin"])
    set_status(client, w["rider1"], order_id, "PICKED_UP")
    assert set_status(client, w["customer"], order_id, "CANCELLED").status_code == 409


def test_rider_cannot_go_off_duty_during_delivery(client):
    w = _setup(client)
    order_id = _new_order(client, w)
    make_ready(client, w["admin"], order_id)
    client.post(f"/orders/{order_id}/assign-rider", headers=w["admin"])
    assert client.patch("/riders/me/availability", headers=w["rider1"]).status_code == 409


def test_notifications_are_created_for_key_actions(client):
    w = _setup(client)
    order_id = _new_order(client, w)
    make_ready(client, w["admin"], order_id)
    client.post(f"/orders/{order_id}/assign-rider", headers=w["admin"])

    customer_msgs = " | ".join(n["message"] for n in client.get("/notifications/", headers=w["customer"]).json())
    assert "placed successfully" in customer_msgs
    assert "accepted" in customer_msgs
    assert "rider has been assigned" in customer_msgs

    admin_msgs = [n["message"] for n in client.get("/notifications/", headers=w["admin"]).json()]
    assert any("New order" in m for m in admin_msgs)

    rider_msgs = [n["message"] for n in client.get("/notifications/", headers=w["rider1"]).json()]
    assert any("assigned delivery" in m for m in rider_msgs)


def test_notifications_are_private_and_need_login(client):
    w = _setup(client)
    _new_order(client, w)
    assert client.get("/notifications/", headers=w["other_customer"]).json() == []
    assert client.get("/notifications/").status_code == 401