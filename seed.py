"""
SmartFoodOps - Database Seeding Script
Populates initial demo data for testing and evaluation.
"""
from sqlalchemy.orm import Session
from app.db.session import SessionLocal, engine, Base
from app.models.user import User
from app.models.restaurant import Restaurant, MenuCategory, MenuItem
from app.core.security import hash_password


def seed_database():
    print("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    try:
        # 1. Seed Users (Admin, Rider, Customer)
        existing_admin = db.query(User).filter(User.email == "admin_kfc@smartfoodops.com").first()
        if not existing_admin:
            admin_user = User(
                name="KFC Admin",
                email="admin_kfc@smartfoodops.com",
                password_hash=hash_password("Password123!"),
                role="restaurant_admin",
                is_active=True,
            )
            db.add(admin_user)
            db.flush()
            print(f"Created Admin: {admin_user.email}")
        else:
            admin_user = existing_admin

        existing_rider = db.query(User).filter(User.email == "kamran_rider@smartfoodops.com").first()
        if not existing_rider:
            rider_user = User(
                name="Kamran Rider",
                email="kamran_rider@smartfoodops.com",
                password_hash=hash_password("Password123!"),
                role="rider",
                is_active=True,
                is_available=True,
            )
            db.add(rider_user)
            db.flush()
            print(f"Created Rider: {rider_user.email}")

        existing_customer = db.query(User).filter(User.email == "customer1@smartfoodops.com").first()
        if not existing_customer:
            customer_user = User(
                name="Customer One",
                email="customer1@smartfoodops.com",
                password_hash=hash_password("Password123!"),
                role="customer",
                is_active=True,
            )
            db.add(customer_user)
            db.flush()
            print(f"Created Customer: {customer_user.email}")

        # 2. Seed Restaurant
        existing_restaurant = db.query(Restaurant).filter(Restaurant.name == "KFC Abbottabad").first()
        if not existing_restaurant:
            restaurant = Restaurant(
                name="KFC Abbottabad",
                description="Finger Lickin' Good fried chicken and fast food",
                cuisine="Fast Food",
                address="Mansehra Road, Mandian, Abbottabad",
                is_open=True,
                owner_user_id=admin_user.id,
            )
            db.add(restaurant)
            db.flush()
            print(f"Created Restaurant: {restaurant.name}")
        else:
            restaurant = existing_restaurant

        # 3. Seed Menu Categories
        cat_burgers = db.query(MenuCategory).filter(
            MenuCategory.restaurant_id == restaurant.id,
            MenuCategory.name == "Burgers"
        ).first()

        if not cat_burgers:
            cat_burgers = MenuCategory(
                restaurant_id=restaurant.id,
                name="Burgers",
                order_index=1,
            )
            db.add(cat_burgers)
            db.flush()
            print("Created Category: Burgers")

        cat_sides = db.query(MenuCategory).filter(
            MenuCategory.restaurant_id == restaurant.id,
            MenuCategory.name == "Sides & Drinks"
        ).first()

        if not cat_sides:
            cat_sides = MenuCategory(
                restaurant_id=restaurant.id,
                name="Sides & Drinks",
                order_index=2,
            )
            db.add(cat_sides)
            db.flush()
            print("Created Category: Sides & Drinks")

        # 4. Seed Menu Items
        item_zinger = db.query(MenuItem).filter(
            MenuItem.category_id == cat_burgers.id,
            MenuItem.name == "Zinger Burger"
        ).first()

        if not item_zinger:
            item_zinger = MenuItem(
                category_id=cat_burgers.id,
                name="Zinger Burger",
                description="Crispy fried chicken burger with lettuce and special mayo",
                price=550.0,
                is_available=True,
                stock=50,
            )
            db.add(item_zinger)
            print("Created Menu Item: Zinger Burger")

        item_fries = db.query(MenuItem).filter(
            MenuItem.category_id == cat_sides.id,
            MenuItem.name == "Hot Crispy Fries"
        ).first()

        if not item_fries:
            item_fries = MenuItem(
                category_id=cat_sides.id,
                name="Hot Crispy Fries",
                description="Golden salted French fries served with ketchup",
                price=250.0,
                is_available=True,
                stock=100,
            )
            db.add(item_fries)
            print("Created Menu Item: Hot Crispy Fries")

        db.commit()
        print("\nDatabase seeding completed successfully! All base demo data ready.")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()