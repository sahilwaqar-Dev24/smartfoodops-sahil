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
    restaurant = db.query(Restaurant).filter(Restaurant.id == order_in.restaurant_id).first()
    if not restaurant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found")

    if not order_in.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order must contain at least one item")

    total_price = 0.0
    order_items = []

    for item_data in order_in.items:
        menu_item = db.query(MenuItem).filter(
            MenuItem.id == item_data.menu_item_id,
            MenuItem.is_available == True
        ).first()

        if not menu_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Menu item {item_data.menu_item_id} not found or unavailable"
            )

        line_total = round(menu_item.price * item_data.quantity, 2)
        total_price += line_total

        order_item = OrderItem(
            menu_item_id=menu_item.id,
            item_name=menu_item.name,
            unit_price=menu_item.price,
            quantity=item_data.quantity,
            line_total=line_total
        )
        order_items.append(order_item)

    new_order = Order(
        customer_id=customer_id,
        restaurant_id=order_in.restaurant_id,
        delivery_address=order_in.delivery_address,
        total_price=round(total_price, 2),
        status=OrderStatus.PLACED,
        items=order_items
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    # Log initial status in history
    history_entry = OrderStatusHistory(
        order_id=new_order.id,
        old_status=None,
        new_status=OrderStatus.PLACED.value,
        changed_by_user_id=customer_id
    )
    db.add(history_entry)
    db.commit()

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