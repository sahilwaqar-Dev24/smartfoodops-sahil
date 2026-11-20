# SmartFoodOps – Demo Script (10 to 15 minutes)

**Before the demo:** delete `smartfoodops.db`, run `python seed.py`, then
`uvicorn app.main:app --reload` and open http://127.0.0.1:8000/docs.
Password for all demo accounts: `Password123!`. In Swagger UI use **Authorize**
(username = email) to switch between users.

## 1. Health and docs (1 min)
- `GET /health` returns `{"status": "ok"}`.
- Show the endpoint groups in `/docs`.

## 2. Customer browses and searches (2 min)
- Authorize as `customer1@smartfoodops.com`.
- `GET /restaurants/` shows 2 restaurants. The closed one (Chapli Kebab Corner) is hidden.
- `GET /restaurants/?cuisine=Desi` and `?name=kfc`.
- `GET /search/menu-items?q=spicy chicken under 500` returns ranked items with a score and `matched_terms`.
- `POST /assistant/recommend` with `{"question": "I want a spicy chicken burger"}`.

## 3. Successful order (2 min)
- `POST /orders/` with this body (items 1 = Zinger Burger Rs. 550, 4 = Hot Crispy Fries Rs. 250):
  ```json
  {"restaurant_id": 1, "delivery_address": "Mandian, Abbottabad",
   "items": [{"menu_item_id": 1, "quantity": 2}, {"menu_item_id": 4, "quantity": 1}]}
  ```
  The server returns `total_price` 1350 and status `PLACED` (the new order id is 5).
- Say: the total comes from database prices, not from the client.

## 4. Failure cases (2 min)
- Order item 5 (Pepsi) with quantity 5: **400**, not enough stock (stock is 3).
- Order from restaurant 3 (closed): **400**, restaurant closed.
- Order item 3 (Discontinued Twister): **400**, item unavailable.
- `POST /restaurants/1/categories` as the customer: **403**.

## 5. Restaurant flow (2 min)
- Authorize as `admin_kfc@smartfoodops.com`. `GET /orders/` shows only KFC orders.
- `PATCH /orders/5/status` with `{"status": "DELIVERED"}`: **409** (invalid jump).
- `POST /orders/5/accept`, then `PATCH /orders/5/status` with `PREPARING` and then `READY`.
- Authorize as `admin_desi@smartfoodops.com` and try `POST /orders/5/accept` again: **403** (not their restaurant).

## 6. Rider flow (2 min)
- As `admin_kfc`: `POST /orders/5/assign-rider`. The status becomes `ASSIGNED` (Kamran, the first available rider).
- Authorize as `ali_rider@smartfoodops.com` and `PATCH /orders/5/status` with `PICKED_UP`: **403** (not the assigned rider).
- Authorize as `kamran_rider@smartfoodops.com`: `PICKED_UP`, then `DELIVERED`.
- `GET /users/me` shows Kamran is available again.

## 7. History, notifications, analytics (2 min)
- As `customer1`: `GET /orders/5/history` shows every step with who changed it. `GET /notifications/` shows the messages.
- As `admin_kfc`: `GET /analytics/platform` (totals, completed, cancelled, average order value, orders per restaurant),
  and again with `?date_from=` and `?date_to=`.

## 8. Tests and code (1 to 2 min)
- Run `python -m pytest -q --cov=app`: 95 tests pass, coverage about 96%.
- Be ready to explain: the `VALID_TRANSITIONS` map in `order_service.py`, first-available rider assignment, and server-side pricing.