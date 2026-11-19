from tests.helpers import PASSWORD, create_user, register


def test_login_wrong_password_is_rejected(client):
    register(client, "user@test.com", "customer")
    res = client.post("/auth/login", data={"username": "user@test.com", "password": "WrongPassword1"})
    assert res.status_code == 401


def test_password_is_hashed_and_never_returned(client, db_session):
    from app.models.user import User
    res = register(client, "hash@test.com", "customer")
    assert res.status_code == 201
    assert "password" not in res.text and "password_hash" not in res.text
    stored = db_session.query(User).filter(User.email == "hash@test.com").first()
    assert stored.password_hash != PASSWORD
    assert stored.password_hash.startswith("$2")  # bcrypt hash


def test_short_password_is_rejected(client):
    res = client.post("/auth/register", json={"name": "A", "email": "a@test.com", "password": "short", "role": "customer"})
    assert res.status_code == 422


def test_invalid_role_is_rejected(client):
    res = client.post("/auth/register", json={"name": "A", "email": "a@test.com", "password": PASSWORD, "role": "superadmin"})
    assert res.status_code == 400


def test_protected_route_rejects_missing_token(client):
    assert client.get("/users/me").status_code == 401
    assert client.get("/orders/").status_code == 401


def test_protected_route_rejects_invalid_token(client):
    res = client.get("/users/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert res.status_code == 401


def test_users_me_returns_current_user(client):
    headers = create_user(client, "me@test.com", "rider")
    res = client.get("/users/me", headers=headers)
    assert res.status_code == 200
    assert res.json()["email"] == "me@test.com"
    assert res.json()["role"] == "rider"