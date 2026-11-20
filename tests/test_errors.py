"""Error handling: consistent JSON, no leaks, health check."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.main import app
from tests.helpers import create_user, register


def test_health_endpoint(client):
    res = client.get("/health")
    assert res.status_code == 200 and res.json() == {"status": "ok"}


def test_unknown_route_returns_consistent_json_error(client):
    res = client.get("/no-such-route")
    assert res.status_code == 404
    assert res.json() == {"error": {"status_code": 404, "message": "Not Found"}}


def test_business_errors_use_the_same_format(client):
    customer = create_user(client, "cust@test.com", "customer")
    res = client.get("/orders/99999", headers=customer)
    assert res.status_code == 404
    assert res.json()["error"]["status_code"] == 404
    assert res.json()["error"]["message"] == "Order not found"


def test_wrong_method_returns_405_json(client):
    res = client.delete("/health")
    assert res.status_code == 405
    assert "error" in res.json()


def test_unauthorized_response_keeps_www_authenticate_header(client):
    res = client.get("/users/me")
    assert res.status_code == 401
    assert res.headers["www-authenticate"] == "Bearer"
    assert res.json()["error"]["status_code"] == 401


def test_validation_error_lists_fields_without_echoing_input(client):
    res = client.post("/auth/register", json={"name": "A", "email": "bad-email", "password": "short"})
    assert res.status_code == 422
    body = res.json()["error"]
    assert body["message"] == "Validation failed"
    fields = {d["field"] for d in body["details"]}
    assert {"email", "password"} <= fields
    assert "short" not in res.text   # user ka password wapas nahi aana chahiye


def test_unexpected_crash_returns_500_without_traceback(client, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("secret internal detail /etc/passwd")

    monkeypatch.setattr("app.api.restaurants.restaurant_service.list_open_restaurants", boom)
    safe_client = TestClient(app, raise_server_exceptions=False)
    res = safe_client.get("/restaurants/")
    assert res.status_code == 500
    assert res.json() == {"error": {"status_code": 500, "message": "Internal server error"}}
    assert "RuntimeError" not in res.text and "passwd" not in res.text and "Traceback" not in res.text


def test_database_error_does_not_leak_sql(client, monkeypatch):
    def db_boom(*args, **kwargs):
        raise OperationalError("SELECT secret_table", {}, Exception("no such table: secret_table"))

    monkeypatch.setattr("app.api.restaurants.restaurant_service.list_open_restaurants", db_boom)
    safe_client = TestClient(app, raise_server_exceptions=False)
    res = safe_client.get("/restaurants/")
    assert res.status_code == 500
    assert "secret_table" not in res.text and "SELECT" not in res.text