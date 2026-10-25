from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.restaurant import Restaurant, MenuItem
from app.models.order import Order, OrderItem, OrderStatusHistory, OrderStatus, PaymentStatus
from app.schemas.order import OrderCreate


# Valid State Transitions Rule Map
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


def create_order(db: Session, customer_id: int, order_in: OrderCreate) -> Order:
    # 1. Restaurant check
    restaurant = db.query(Restaurant).filter(Restaurant.id == order_in.restaurant_id).first()
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found"
        )
    if not restaurant.is_open:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Restaurant is currently closed and not accepting orders"
        )

    # 2. Server-side dynamic price calculation & stock validation
    calculated_total = 0.0
    order_items_to_create = []

    for item_data in order_in.items:
        menu_item = db.query(MenuItem).filter(MenuItem.id == item_data.menu_item_id).first()
        if not menu_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Menu item with ID {item_data.menu_item_id} not found"
            )
        
        # Verify item belongs to the requested restaurant
        if menu_item.category.restaurant_id != restaurant.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Menu item '{menu_item.name}' does not belong to this restaurant"
            )

        # Availability check
        if not menu_item.is_available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Menu item '{menu_item.name}' is currently unavailable"
            )

        # Stock check
        if menu_item.stock < item_data.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for '{menu_item.name}'. Available: {menu_item.stock}, Requested: {item_data.quantity}"
            )

        # Deduct stock
        menu_item.stock -= item_data.quantity
        db.add(menu_item)

        line_total = round(menu_item.price * item_data.quantity, 2)
        calculated_total += line_total

        order_item = OrderItem(
            menu_item_id=menu_item.id,
            item_name=menu_item.name,
            unit_price=menu_item.price,
            quantity=item_data.quantity,
            line_total=line_total
        )
        order_items_to_create.append(order_item)

    calculated_total = round(calculated_total, 2)

    # 3. Create Order
    new_order = Order(
        customer_id=customer_id,
        restaurant_id=restaurant.id,
        total_price=calculated_total,
        status=OrderStatus.PLACED,
        payment_status=PaymentStatus.PENDING,
        delivery_address=order_in.delivery_address
    )
    db.add(new_order)
    db.flush()  # Generate order id

    # 4. Attach items to order
    for oi in order_items_to_create:
        oi.order_id = new_order.id
        db.add(oi)

    # 5. Audit Log (History)
    history = OrderStatusHistory(
        order_id=new_order.id,
        old_status=None,
        new_status=OrderStatus.PLACED.value,
        changed_by_user_id=customer_id
    )
    db.add(history)

    db.commit()
    db.refresh(new_order)
    return new_order


def transition_order_status(db: Session, order: Order, new_status: OrderStatus, user_id: int) -> Order:
    current_status = order.status

    # Validate transition
    allowed = VALID_TRANSITIONS.get(current_status, [])
    if new_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invalid status transition from {current_status.value} to {new_status.value}"
        )

    # Status update & History tracking
    old_status_val = current_status.value
    order.status = new_status

    history = OrderStatusHistory(
        order_id=order.id,
        old_status=old_status_val,
        new_status=new_status.value,
        changed_by_user_id=user_id
    )
    db.add(history)
    db.add(order)
    db.commit()
    db.refresh(order)
    return order