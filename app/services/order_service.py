from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.order import Order, OrderItem, OrderStatus, OrderStatusHistory
from app.models.restaurant import MenuItem, Restaurant
from app.models.user import User
from app.schemas.order import OrderCreate

VALID_TRANSITIONS = {
    OrderStatus.PLACED: [OrderStatus.ACCEPTED, OrderStatus.CANCELLED],
    OrderStatus.ACCEPTED: [OrderStatus.PREPARING, OrderStatus.CANCELLED],
    OrderStatus.PREPARING: [OrderStatus.READY],
    OrderStatus.READY: [OrderStatus.ASSIGNED],
    OrderStatus.ASSIGNED: [OrderStatus.PICKED_UP],
    OrderStatus.PICKED_UP: [OrderStatus.DELIVERED],
    OrderStatus.DELIVERED: [],
    OrderStatus.CANCELLED: []
}

def create_order(db: Session, order_in: OrderCreate, customer_id: int) -> Order:
    # 1. Restaurant check
    restaurant = db.query(Restaurant).filter(Restaurant.id == order_in.restaurant_id).first()
    if not restaurant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found")

    if not restaurant.is_open:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Restaurant is currently closed and cannot accept orders"
        )

    # 2. Cart check
    if not order_in.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order must contain at least one item")

    # Agar same item cart mein 2 baar aaye to quantity jama kar do
    requested = {}
    for item_data in order_in.items:
        requested[item_data.menu_item_id] = requested.get(item_data.menu_item_id, 0) + item_data.quantity

    total_price = 0.0
    order_items = []
    stock_updates = []  # (menu_item, quantity) payment success hone ke baad stock kam hoga

    # 3. Har item ki validation
    for menu_item_id, quantity in requested.items():
        menu_item = db.query(MenuItem).filter(MenuItem.id == menu_item_id).first()

        if not menu_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Menu item {menu_item_id} not found"
            )

        # Item isi restaurant ka hona chahiye
        if menu_item.category.restaurant_id != order_in.restaurant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Menu item '{menu_item.name}' does not belong to this restaurant"
            )

        if not menu_item.is_available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Menu item '{menu_item.name}' is currently unavailable"
            )

        if menu_item.stock is not None and quantity > menu_item.stock:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for '{menu_item.name}'. Requested {quantity}, available {menu_item.stock}"
            )

        line_total = round(menu_item.price * quantity, 2)
        total_price += line_total

        order_items.append(OrderItem(
            menu_item_id=menu_item.id,
            item_name=menu_item.name,
            unit_price=menu_item.price,
            quantity=quantity,
            line_total=line_total
        ))
        stock_updates.append((menu_item, quantity))

    # 4. Payment simulation
    payment_ok = order_in.simulate_payment == "PAID"

    if payment_ok:
        order_status = OrderStatus.PLACED
        for menu_item, quantity in stock_updates:
            if menu_item.stock is not None:
                menu_item.stock -= quantity
    else:
        # Payment fail: order record rehta hai magar CANCELLED, aur stock kam nahi hota
        order_status = OrderStatus.CANCELLED

    new_order = Order(
        customer_id=customer_id,
        restaurant_id=order_in.restaurant_id,
        delivery_address=order_in.delivery_address,
        total_price=round(total_price, 2),
        status=order_status,
        payment_status=order_in.simulate_payment,
        items=order_items
    )
    db.add(new_order)
    db.flush()

    # 5. Pehli history entry
    history_entry = OrderStatusHistory(
        order_id=new_order.id,
        old_status=None,
        new_status=order_status.value,
        changed_by_user_id=customer_id
    )
    db.add(history_entry)
    db.commit()
    db.refresh(new_order)

    return new_order

def assign_rider_to_order(db: Session, order_id: int, current_user: User, rider_id: int = None) -> Order:
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    # Only restaurant admin can assign rider
    if current_user.role != "restaurant_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only restaurant admins are authorized to assign riders"
        )

    restaurant = db.query(Restaurant).filter(Restaurant.id == order.restaurant_id).first()
    if not restaurant or restaurant.owner_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to manage orders for this restaurant"
        )

    if order.status != OrderStatus.READY:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Order must be in READY status before assigning a rider (current status: {order.status})"
        )

    # Pick rider: either requested rider_id or auto-pick first available
    if rider_id:
        rider = db.query(User).filter(
            User.id == rider_id,
            User.role == "rider",
            User.is_active == True,
            User.is_available == True
        ).first()
        if not rider:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected rider is not available or does not exist"
            )
    else:
        rider = db.query(User).filter(
            User.role == "rider",
            User.is_active == True,
            User.is_available == True
        ).first()
        if not rider:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No available riders found"
            )

    old_status = order.status
    order.rider_id = rider.id
    order.status = OrderStatus.ASSIGNED
    rider.is_available = False

    history_entry = OrderStatusHistory(
        order_id=order.id,
        old_status=old_status.value if hasattr(old_status, 'value') else str(old_status),
        new_status=OrderStatus.ASSIGNED.value,
        changed_by_user_id=current_user.id
    )
    db.add(history_entry)
    db.commit()
    db.refresh(order)
    return order

def update_order_status(db: Session, order_id: int, new_status: OrderStatus, current_user: User) -> Order:
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    # State machine transition check
    allowed_transitions = VALID_TRANSITIONS.get(order.status, [])
    if new_status not in allowed_transitions:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invalid status transition from {order.status} to {new_status}"
        )

    # Role validation per transition
    if new_status in [OrderStatus.ACCEPTED, OrderStatus.PREPARING, OrderStatus.READY]:
        if current_user.role != "restaurant_admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only restaurant admins are authorized to perform this action"
            )
        restaurant = db.query(Restaurant).filter(Restaurant.id == order.restaurant_id).first()
        if not restaurant or restaurant.owner_user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to update orders for this restaurant"
            )

    elif new_status in [OrderStatus.PICKED_UP, OrderStatus.DELIVERED]:
        # Only the assigned rider can mark picked up or delivered
        if current_user.role != "rider":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only riders are authorized to update delivery progress"
            )
        if order.rider_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the assigned rider can update this order"
            )

    old_status = order.status
    order.status = new_status

    # If delivered, free up the rider
    if new_status == OrderStatus.DELIVERED and order.rider_id:
        assigned_rider = db.query(User).filter(User.id == order.rider_id).first()
        if assigned_rider:
            assigned_rider.is_available = True

    history_entry = OrderStatusHistory(
        order_id=order.id,
        old_status=old_status.value if hasattr(old_status, 'value') else str(old_status),
        new_status=new_status.value if hasattr(new_status, 'value') else str(new_status),
        changed_by_user_id=current_user.id
    )
    db.add(history_entry)
    db.commit()
    db.refresh(order)
    return order