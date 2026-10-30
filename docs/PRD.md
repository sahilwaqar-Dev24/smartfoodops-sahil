# Product Requirements Document (PRD) - SmartFoodOps

## 1. Project Goal
SmartFoodOps provides a backend operations system for food ordering, menu administration, automated rider dispatch, and business intelligence reporting.

---

## 2. Target Roles & Capabilities

### 2.1 Customer
- Browse restaurants and active menus.
- Place orders with automatic server-calculated item totals.
- Track real-time order lifecycle status.

### 2.2 Restaurant Admin
- Manage restaurant information and category-wise menu listings.
- Update dish availability and stock levels.
- Process orders: move status from `PLACED` to `ACCEPTED`, `PREPARING`, and `READY`.
- Access restaurant-specific sales metrics.

### 2.3 Rider
- Toggle on/off duty availability (`is_available`).
- Receive assigned delivery tasks.
- Advance delivery states: `PICKED_UP` and `DELIVERED`.

### 2.4 Platform Operations
- Access platform-level aggregate metrics (total volume, cancellations, gross revenue).
- Perform TF-IDF text search across available dishes.

---

## 3. Core Acceptance Criteria

- **Security**: JWT bearer authentication enforced on all protected endpoints.
- **Data Protection**: Client cannot tamper with prices; unit price must be fetched from the database at order creation.
- **State Integrity**: Invalid jumps across the order state machine return HTTP `409 Conflict`.
- **Rider Isolation**: Non-admin roles receive HTTP `403 Forbidden` when attempting to query all available riders.
- **Auditability**: Every order transition appends a history record with timestamp and user ID.