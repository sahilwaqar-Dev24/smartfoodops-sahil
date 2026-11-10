# SmartFoodOps - System Architecture & Design

## 1. System Overview
SmartFoodOps is an operations-focused backend REST API built using FastAPI, SQLAlchemy, and SQLite. It handles the complete food delivery lifecycle, including role-based authentication (RBAC), multi-tenant restaurant and menu management, server-side dynamic pricing, sequential order state machine transitions, automated rider dispatching, platform analytics, and TF-IDF intelligent search retrieval.

---

## 2. Order Lifecycle State Machine
The order lifecycle strictly enforces valid sequential status transitions. Skipping steps or illegal transitions immediately reject the request with an **HTTP 409 Conflict** error.

```text
[PLACED]
   │
   ▼
[ACCEPTED]      (Action by: Restaurant Admin)
   │
   ▼
[PREPARING]     (Action by: Restaurant Admin)
   │
   ▼
[READY]         (Action by: Restaurant Admin)
   │
   ▼
[ASSIGNED]      (Auto-dispatch / Manual First-Available Rider)
   │
   ▼
[PICKED_UP]     (Action by: Assigned Rider only)
   │
   ▼
[DELIVERED]     (Action by: Assigned Rider only)