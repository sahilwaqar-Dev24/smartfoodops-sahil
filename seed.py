"""
SmartFoodOps - Demo data seed script.

Chalane ka tareeqa:  python seed.py
Script dobara chalane par duplicate data nahi banta.
"""
from datetime import datetime, timedelta

from app.core.security import hash_password
from app.db.session import Base, SessionLocal, engine
import app.models  # noqa: F401
from app.models.notification import Notification
from app.models.order import Order, OrderItem, OrderStatus, OrderStatusHistory
from app.models.restaurant import MenuCategory, MenuItem, Restaurant
from app.models.user import User

PASSWORD = "Password123!"

# (naam, email, role)
USERS = [
    ("KFC Admin", "admin_kfc@smartfoodops.com", "restaurant_admin"),
    ("Desi Kitchen Admin", "admin_desi@smartfoodops.com", "restaurant_admin"),
    ("Kamran Rider", "kamran_rider@smartfoodops.com", "rider"),
    ("Ali Rider", "ali_rider@smartfoodops.com", "rider"),
    ("Customer One", "customer1@smartfoodops.com", "customer"),
    ("Customer Two", "customer2@smartfoodops.com", "customer"),
]

# (owner email, naam, cuisine, address, is_open)
RESTAURANTS = [
    ("admin_kfc@smartfoodops.com", "KFC Abbottabad", "Fast Food", "Mandian, Abbottabad", True),
    ("admin_desi@smartfoodops.com", "Desi Kitchen", "Desi", "Jinnahabad, Abbottabad", True),
    ("admin_desi@smartfoodops.com", "Chapli Kebab Corner", "Desi", "Mall Road, Abbottabad", False),
]

# (restaurant, category, item, description, price, stock, available)
MENU = [
    ("KFC Abbottabad", "Burgers", "Zinger Burger",
     "Crispy fried chicken burger with lettuce and special mayo", 550, 50, True),
    ("KFC Abbottabad", "Burgers", "Spicy Wings Burger",
     "Hot and spicy chicken wings burger with chilli sauce", 650, 30, True),
    ("KFC Abbottabad", "Burgers", "Discontinued Twister",
     "Old wrap, no longer sold", 400, 10, False),
    ("KFC Abbottabad", "Sides and Drinks", "Hot Crispy Fries",
     "Golden salted French fries served with ketchup", 250, 100, True),
    ("KFC Abbottabad", "Sides and Drinks", "Pepsi",
     "Cold drink 500ml", 120, 3, True),
    ("Desi Kitchen", "Rice and Curries", "Chicken Biryani",
     "Spicy chicken biryani with raita and salad", 450, 40, True),
    ("Desi Kitchen", "Rice and Curries", "Chicken Karahi",
     "Spicy chicken karahi cooked in tomatoes and green chilli", 1100, 20, True),
    ("Desi Kitchen", "Rice and Curries", "Seekh Kebab Plate",
     "Grilled beef seekh kebab with naan and chutney", 600, 25, True),
    ("Chapli Kebab Corner", "Kebabs", "Chapli Kebab",
     "Peshawari beef chapli kebab", 350, 20, True),
]

# (restaurant, [(item, quantity)], status, kitne din pehle, rider hai?)
DEMO_ORDERS = [
    ("KFC Abbottabad", [("Zinger Burger", 2), ("Hot Crispy Fries", 1)], "DELIVERED", 3, True),
    ("KFC Abbottabad", [("Zinger Burger", 1)], "DELIVERED", 1, True),
    ("KFC Abbottabad", [("Hot Crispy Fries", 2)], "CANCELLED", 2, False),
    ("Desi Kitchen", [("Chicken Biryani", 2)], "DELIVERED", 1, True),
]

DELIVERED_PATH = ["PLACED", "ACCEPTED", "PREPARING", "READY", "ASSIGNED", "PICKED_UP", "DELIVERED"]


def seed_users(db):
    for name, email, role in USERS:
        if db.query(User).filter(User.email == email).first():
            continue
        db.add(User(name=name, email=email, role=role, password_hash=hash_password(PASSWORD)))
        print("  + user:", email, role)
    db.flush()


def seed_restaurants(db):
    for owner_email, name, cuisine, address, is_open in RESTAURANTS:
        if db.query(Restaurant).filter(Restaurant.name == name).first():
            continue
        owner = db.query(User).filter(User.email == owner_email).first()
        db.add(Restaurant(owner_user_id=owner.id, name=name, cuisine=cuisine,
                          address=address, description=name, is_open=is_open))
        print("  + restaurant:", name, "open" if is_open else "closed")
    db.flush()


def seed_menu(db):
    for restaurant_name, category_name, item_name, description, price, stock, available in MENU:
        restaurant = db.query(Restaurant).filter(Restaurant.name == restaurant_name).first()
        category = db.query(MenuCategory).filter(
            MenuCategory.restaurant_id == restaurant.id,
            MenuCategory.name == category_name,
        ).first()
        if not category:
            category = MenuCategory(restaurant_id=restaurant.id, name=category_name)
            db.add(category)
            db.flush()
        exists = db.query(MenuItem).filter(
            MenuItem.category_id == category.id, MenuItem.name == item_name
        ).first()
        if exists:
            continue
        db.add(MenuItem(category_id=category.id, name=item_name, description=description,
                        price=price, stock=stock, is_available=available))
        print("  + item:", item_name, price)
    db.flush()


def find_item(db, restaurant_id, item_name):
    return (
        db.query(MenuItem)
        .join(MenuCategory, MenuItem.category_id == MenuCategory.id)
        .filter(MenuCategory.restaurant_id == restaurant_id, MenuItem.name == item_name)
        .first()
    )


def seed_demo_orders(db):
    if db.query(Order).count() > 0:
        return
    customer = db.query(User).filter(User.email == "customer1@smartfoodops.com").first()
    rider = db.query(User).filter(User.email == "kamran_rider@smartfoodops.com").first()

    for restaurant_name, lines, status, days_ago, has_rider in DEMO_ORDERS:
        restaurant = db.query(Restaurant).filter(Restaurant.name == restaurant_name).first()
        created = datetime.utcnow() - timedelta(days=days_ago)

        items = []
        total = 0.0
        for item_name, quantity in lines:
            menu_item = find_item(db, restaurant.id, item_name)
            line_total = menu_item.price * quantity
            total += line_total
            items.append(OrderItem(menu_item_id=menu_item.id, item_name=menu_item.name,
                                   unit_price=menu_item.price, quantity=quantity,
                                   line_total=line_total))

        order = Order(customer_id=customer.id, restaurant_id=restaurant.id,
                      rider_id=rider.id if has_rider else None,
                      total_price=total, status=OrderStatus(status), payment_status="PAID",
                      delivery_address="House 12, Main Road, Abbottabad",
                      created_at=created, updated_at=created, items=items)
        db.add(order)
        db.flush()

        path = DELIVERED_PATH if status == "DELIVERED" else ["PLACED", status]
        for step in range(len(path)):
            old_status = path[step - 1] if step > 0 else None
            db.add(OrderStatusHistory(order_id=order.id, old_status=old_status,
                                      new_status=path[step], changed_by_user_id=customer.id,
                                      changed_at=created + timedelta(minutes=5 * step)))
        db.add(Notification(user_id=customer.id, order_id=order.id,
                            message="Order #%s is %s" % (order.id, status), created_at=created))
        print("  + demo order:", restaurant_name, status, total)


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        print("Users:")
        seed_users(db)
        print("Restaurants:")
        seed_restaurants(db)
        print("Menu items:")
        seed_menu(db)
        print("Demo orders:")
        seed_demo_orders(db)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print()
    print("Seeding complete. Demo logins (password for all: Password123!)")
    print("  restaurant admin: admin_kfc@smartfoodops.com, admin_desi@smartfoodops.com")
    print("  rider:            kamran_rider@smartfoodops.com, ali_rider@smartfoodops.com")
    print("  customer:         customer1@smartfoodops.com, customer2@smartfoodops.com")


if __name__ == "__main__":
    main()