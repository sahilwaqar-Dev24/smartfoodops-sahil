import logging
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.order import Order, OrderItem, OrderStatus, OrderStatusHistory
from app.models.restaurant import MenuItem, Restaurant
from app.models.user import User
from app.schemas.order import OrderCreate
from app.services.notification_service import create_notification

logger = logging.getLogger("smartfoodops.orders")

# PDF: cancellation PICKED_UP se pehle kabhi bhi allowed hai
VALID_TRANSITIONS = {
    OrderStatus.PLACED: [OrderStatus.ACCEPTED, OrderStatus.REJECTED, OrderStatus.CANCELLED],
    OrderStatus.ACCEPTED: [OrderStatus.PREPARING, OrderStatus.CANCELLED],
    OrderStatus.PREPARING: [OrderStatus.READY, OrderStatus.CANCELLED],
    OrderStatus.READY: [OrderStatus.ASSIGNED, OrderStatus.CANCELLED],
    OrderStatus.ASSIGNED: [OrderStatus.PICKED_UP, OrderStatus.CANCELLED],
    OrderStatus.PICKED_UP: [OrderStatus.DELIVERED],
    OrderStatus.DELIVERED: [],
    OrderStatus.CANCELLED: [],
    OrderStatus.REJECTED: [],
}

# Customer ko bheje jaane wale notification messages
CUSTOMER_MESSAGES = {
    OrderStatus.ACCEPTED: "Order #{id} accepted by the restaurant",
    OrderStatus.REJECTED: "Order #{id} was rejected by the restaurant",
    OrderStatus.PREPARING: "Order #{id} is being prepared",
    OrderStatus.READY: "Order #{id} is ready for pickup",
    OrderStatus.PICKED_UP: "Order #{id} has been picked up by the rider",
    OrderStatus.DELIVERED: "Order #{id} has been delivered",
    OrderStatus.CANCELLED: "Order #{id} has been cancelled",
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

    # 6. Notifications (usi request ke andar)
    if payment_ok:
        create_notification(db, customer_id, f"Order #{new_order.id} placed successfully", new_order.id)
        create_notification(db, restaurant.owner_user_id, f"New order #{new_order.id} received", new_order.id)
    else:
        create_notification(db, customer_id, f"Payment failed for order #{new_order.id}. Order cancelled", new_order.id)

    db.commit()
    db.refresh(new_order)

    logger.info(
        "order_created order_id=%s customer_id=%s restaurant_id=%s total=%s payment=%s status=%s",
        new_order.id, customer_id, order_in.restaurant_id, new_order.total_price,
        new_order.payment_status, order_status.value
    )
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
            logger.warning("rider_assign_failed order_id=%s reason=selected_rider_unavailable rider_id=%s", order_id, rider_id)
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
            logger.warning("rider_assign_failed order_id=%s reason=no_available_rider", order_id)
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

    create_notification(db, order.customer_id, f"A rider has been assigned to order #{order.id}", order.id)
    create_notification(db, rider.id, f"You have been assigned delivery for order #{order.id}", order.id)

    db.commit()
    db.refresh(order)

    logger.info("rider_assigned order_id=%s rider_id=%s by_user_id=%s", order.id, rider.id, current_user.id)
    return order

def update_order_status(db: Session, order_id: int, new_status: OrderStatus, current_user: User) -> Order:
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    # State machine transition check
    allowed_transitions = VALID_TRANSITIONS.get(order.status, [])
    if new_status not in allowed_transitions:
        logger.warning(
            "invalid_transition order_id=%s from=%s to=%s user_id=%s",
            order.id, order.status.value, new_status.value, current_user.id
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invalid status transition from {order.status.value} to {new_status.value}"
        )

    # ASSIGNED sirf assign-rider endpoint se hoga, PATCH se nahi
    if new_status == OrderStatus.ASSIGNED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use the assign-rider endpoint to assign a rider"
        )

    restaurant = db.query(Restaurant).filter(Restaurant.id == order.restaurant_id).first()

    # Role validation per transition
    if new_status in [OrderStatus.ACCEPTED, OrderStatus.REJECTED, OrderStatus.PREPARING, OrderStatus.READY]:
        if current_user.role != "restaurant_admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only restaurant admins are authorized to perform this action"
            )
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

    elif new_status == OrderStatus.CANCELLED:
        # Sirf order ka apna customer ya us restaurant ka admin cancel kar sakta hai
        if current_user.role == "customer":
            if order.customer_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only cancel your own orders"
                )
        elif current_user.role == "restaurant_admin":
            if not restaurant or restaurant.owner_user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not authorized to cancel orders for this restaurant"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Riders are not allowed to cancel orders"
            )

    old_status = order.status
    order.status = new_status

    # Cancel ya reject hone pe: rider free karo aur stock wapas karo
    if new_status in [OrderStatus.CANCELLED, OrderStatus.REJECTED]:
        if order.rider_id:
            freed_rider = db.query(User).filter(User.id == order.rider_id).first()
            if freed_rider:
                freed_rider.is_available = True
        if order.payment_status == "PAID":
            for order_item in order.items:
                menu_item = db.query(MenuItem).filter(MenuItem.id == order_item.menu_item_id).first()
                if menu_item and menu_item.stock is not None:
                    menu_item.stock += order_item.quantity

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

    # Notifications
    message = CUSTOMER_MESSAGES[new_status].format(id=order.id)
    create_notification(db, order.customer_id, message, order.id)
    if new_status == OrderStatus.CANCELLED:
        if order.rider_id:
            create_notification(db, order.rider_id, f"Order #{order.id} was cancelled", order.id)
        if current_user.role == "customer" and restaurant:
            create_notification(db, restaurant.owner_user_id, f"Order #{order.id} was cancelled by the customer", order.id)

    db.commit()
    db.refresh(order)

    logger.info(
        "order_status_changed order_id=%s from=%s to=%s by_user_id=%s",
        order.id, old_status.value, new_status.value, current_user.id
    )
    return order