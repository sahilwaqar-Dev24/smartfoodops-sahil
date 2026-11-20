# SmartFoodOps – ERD

```mermaid
erDiagram
    USERS ||--o{ RESTAURANTS : owns
    USERS ||--o{ ORDERS : "places (customer)"
    USERS ||--o{ ORDERS : "delivers (rider)"
    USERS ||--o{ NOTIFICATIONS : receives
    USERS ||--o{ ORDER_STATUS_HISTORY : changes
    RESTAURANTS ||--o{ MENU_CATEGORIES : has
    RESTAURANTS ||--o{ ORDERS : receives
    MENU_CATEGORIES ||--o{ MENU_ITEMS : contains
    MENU_ITEMS ||--o{ ORDER_ITEMS : "ordered as"
    ORDERS ||--|{ ORDER_ITEMS : contains
    ORDERS ||--o{ ORDER_STATUS_HISTORY : "has history"
    ORDERS ||--o{ NOTIFICATIONS : "triggers"

    USERS {
        int id PK
        string name
        string email
        string password_hash
        string role "customer, restaurant_admin, rider"
        bool is_active
        bool is_available "used by riders"
        datetime created_at
    }
    RESTAURANTS {
        int id PK
        int owner_user_id FK
        string name
        string description
        string cuisine
        string address
        bool is_open
        datetime created_at
    }
    MENU_CATEGORIES {
        int id PK
        int restaurant_id FK
        string name
        int order_index
    }
    MENU_ITEMS {
        int id PK
        int category_id FK
        string name
        string description
        float price
        bool is_available
        int stock
        datetime created_at
    }
    ORDERS {
        int id PK
        int customer_id FK
        int restaurant_id FK
        int rider_id FK "nullable"
        float total_price
        string status
        string payment_status "PENDING, PAID, FAILED"
        string delivery_address
        datetime created_at
        datetime updated_at
    }
    ORDER_ITEMS {
        int id PK
        int order_id FK
        int menu_item_id FK
        string item_name "snapshot"
        float unit_price "snapshot"
        int quantity
        float line_total
    }
    ORDER_STATUS_HISTORY {
        int id PK
        int order_id FK
        string old_status
        string new_status
        int changed_by_user_id FK
        datetime changed_at
    }
    NOTIFICATIONS {
        int id PK
        int user_id FK
        int order_id FK "nullable"
        string message
        datetime created_at
    }
```

**Notes**

- `orders.status` holds one of: PLACED, ACCEPTED, REJECTED, PREPARING, READY, ASSIGNED, PICKED_UP, DELIVERED, CANCELLED.
- `order_items` copies the name and unit price when the order is placed, so old orders do not change if the menu changes.
- A user is a customer, a restaurant admin or a rider depending on `role`. `orders.customer_id` and `orders.rider_id` both point to `users`.