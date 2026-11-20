# SmartFoodOps – Product Requirements (short PRD)

## 1. Goal

QuickServe wants a small, clear backend for food ordering and delivery. Customers order food,
restaurants prepare it and riders deliver it. The project should work from login to a delivered order
and be easy to explain.

## 2. Main users

| User | Needs |
|------|-------|
| **Customer** | Find open restaurants and available food, place an order with a correct total, follow its status. |
| **Restaurant admin** | Manage their own restaurant and menu, accept or reject orders, prepare them, see simple numbers. |
| **Rider** | Be assigned a delivery, mark it picked up and delivered. |

## 3. Main use cases

1. Register and log in with a role.
2. Admin creates a restaurant, categories and menu items.
3. Customer browses and searches restaurants and menus.
4. Customer places an order. The server checks the cart and calculates the total.
5. Admin accepts or rejects the order, then moves it to PREPARING and READY.
6. An available rider is assigned and the rider delivers the order.
7. Everybody involved receives notifications and the customer can see the status history.
8. Admin views analytics (orders, completed, cancelled, average order value, orders per restaurant).
9. Customer searches food in plain words and asks the assistant for a recommendation.

## 4. Requirements

**Must have (all done)**
- Registration and login with hashed passwords, JWT, three roles, server-side permission and ownership checks.
- Restaurants, categories and menu items with create, update, list and remove.
- Order placement with validation (cart, open restaurant, availability, stock) and server-side pricing.
- Simulated payment status (PAID, PENDING, FAILED).
- Order status flow with 409 on invalid changes and a status history.
- Rider availability, first-available assignment and delivery steps.
- Notifications table, analytics endpoints, `GET /health`, logging, consistent JSON errors.
- Seed data, at least 12 automated tests (there are 95), README, ERD and design notes.

**Should have (done)**
- `/users/me`, pagination, cancel before pickup, clear message when no rider is available,
  date filters for analytics, test coverage above 60% (about 96%).

**Stretch (not done on purpose)**
- Admin role, soft delete, duplicate-order protection with `client_request_id`, average delivery time,
  Celery and Redis, Docker, reassigning riders.

**Search and assistant (weeks 4 and 5)**
- Ranked TF-IDF menu search with cuisine and price filters and a rule-based assistant that only uses retrieved menu items.

## 5. Out of scope

Real payments, a front end, maps and tracking, distributed systems, concurrency locking and vector databases.

## 6. Weekly milestones

| Week | Goal | Result |
|------|------|--------|
| 1 | Setup, `/health`, ERD, auth, roles, restaurants, menus, seed, first tests | Done |
| 2 | Orders, pricing, stock, status flow, riders, notifications, more tests | Done |
| 3 | Analytics, logging, error handling, 12+ tests, docs, Part A demo | Done |
| 4 | Menu search: keyword relevance, TF-IDF ranking, filters, search tests | Done |
| 5 | Food assistant, cleanup, final tests, README, final demo | Done |

## 7. Success measures

- The full flow (customer order to delivered) works from Swagger UI in a few minutes using the seed data.
- Permissions, prices, stock and status rules are enforced on the server (and covered by tests).
- A fresh clone can be set up from the README and all tests pass.