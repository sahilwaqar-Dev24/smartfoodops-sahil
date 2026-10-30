"""
Pytest configuration and test database fixtures for SmartFoodOps.
Uses an in-memory SQLite database to ensure tests remain isolated.
"""
import os
import sys

# Project root directory ko Python search path mein include karna
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.session import Base, get_db
from app.main import app
from app.models.restaurant import MenuCategory, MenuItem, Restaurant
from app.models.user import User

# In-memory SQLite for clean test isolation
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create fresh tables for every test function and tear them down after."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI TestClient with overridden get_db dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def seeded_users(db_session):
    """Seed base test users."""
    admin = User(
        name="KFC Admin",
        email="admin@test.com",
        password_hash=hash_password("Password123!"),
        role="restaurant_admin",
        is_active=True,
    )
    rider = User(
        name="Kamran Rider",
        email="rider@test.com",
        password_hash=hash_password("Password123!"),
        role="rider",
        is_active=True,
        is_available=True,
    )
    customer = User(
        name="Customer One",
        email="customer@test.com",
        password_hash=hash_password("Password123!"),
        role="customer",
        is_active=True,
    )
    db_session.add_all([admin, rider, customer])
    db_session.commit()
    db_session.refresh(admin)
    db_session.refresh(rider)
    db_session.refresh(customer)
    return {"admin": admin, "rider": rider, "customer": customer}


@pytest.fixture
def seeded_restaurant(db_session, seeded_users):
    """Seed test restaurant with categories and items."""
    admin = seeded_users["admin"]
    restaurant = Restaurant(
        name="KFC Abbottabad",
        description="Fast Food",
        cuisine="Fast Food",
        address="Mandian, Abbottabad",
        is_open=True,
        owner_user_id=admin.id,
    )
    db_session.add(restaurant)
    db_session.commit()
    db_session.refresh(restaurant)

    category = MenuCategory(
        restaurant_id=restaurant.id,
        name="Burgers",
        order_index=1,
    )
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)

    item1 = MenuItem(
        category_id=category.id,
        name="Zinger Burger",
        description="Crispy spicy chicken burger",
        price=550.0,
        is_available=True,
        stock=50,
    )
    item2 = MenuItem(
        category_id=category.id,
        name="Crispy Fries",
        description="Salted golden french fries",
        price=250.0,
        is_available=True,
        stock=100,
    )
    db_session.add_all([item1, item2])
    db_session.commit()
    db_session.refresh(item1)
    db_session.refresh(item2)

    return {"restaurant": restaurant, "category": category, "items": [item1, item2]}