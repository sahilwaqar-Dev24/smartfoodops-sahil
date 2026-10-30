# SmartFoodOps System Architecture & Design

## 1. System Overview
SmartFoodOps is an operations-focused backend system for online food ordering and delivery. It uses a layered modular architecture with clear separation between endpoints, validation schemas, database models, and service layer business logic.

---

## 2. Order Lifecycle State Machine

The order lifecycle follows strict sequential state transitions:

```text
[PLACED]
   │
   ▼
[ACCEPTED]        (Restaurant Admin)
   │
   ▼
[PREPARING]       (Restaurant Admin)
   │
   ▼
[READY]           (Restaurant Admin)
   │
   ▼
[ASSIGNED]        (Auto / Admin Dispatch)
   │
   ▼
[PICKED_UP]       (Assigned Rider)
   │
   ▼
[DELIVERED]       (Assigned Rider)