# Engineering Notes – SmartFoodOps

Progress tracker, decisions and problems solved while building the project.

## 1. Progress tracker

| Task | Status | Notes |
|------|--------|-------|
| Project setup, `/health`, settings | Done | Layered folders, SQLite, `.env` for secrets |
| Auth, JWT, roles | Done | bcrypt hashes, three roles, `/users/me` |
| Restaurants, menus | Done | Owner checks, search, pagination, delete rules |
| Orders, pricing, stock | Done | Server-side prices, price snapshot, simulated payment |
| Status flow, history | Done | One transition map, 409 on invalid jumps |
| Riders | Done | First-available assignment, availability lock during delivery |
| Notifications, logging, errors | Done | Notification rows, Python logging, one JSON error format |
| Analytics | Done | Totals, average, per restaurant, date filters |
| Search and assistant | Done | TF-IDF ranking, filters, rule-based assistant |
| Tests | Done | 95 tests, about 96% coverage |
| Docs | Done | README, design, ERD, PRD, demo script |

## 2. Review round (problems found and fixed)

A full review against the assignment PDFs found these problems. All are fixed:

- Orders routes had no `/orders` prefix, so the URLs were wrong.
- Stock was not checked or reduced, closed restaurants accepted orders, items from another restaurant were accepted, negative quantities were accepted.
- Any user could cancel or read any order. Admins could see every order.
- No `REJECTED` status, no notifications table, no logging, no payment simulation.
- No restaurant search, pagination or delete endpoints.
- JWT secret was written in the code (now read from `.env`).
- Errors had different shapes and could leak internal details.
- Passwords of any length were accepted.
- Auth, restaurant and search logic sat inside routes or in the wrong service.
- Tests were weak (14 happy-path tests), now 95 tests including permission and failure cases.

## 3. Technical decisions

- **Server-side pricing:** the client sends only item ids and quantities. The price comes from the database and is copied into `order_items`.
- **One transition map:** `VALID_TRANSITIONS` in `order_service.py` is the only place that decides which status changes are allowed.
- **`ASSIGNED` only via `assign-rider`:** it must also pick a rider and mark the rider unavailable, so it cannot be set by a plain status update.
- **Delete rule:** a menu item or category that appears in past orders cannot be deleted (409). The admin marks it unavailable.
- **Analytics scope:** an admin sees only their own restaurants.
- **Search threshold:** results below cosine similarity 0.05 are dropped so unrelated queries return an empty list.

## 4. Errors I solved

- **Python 3.14 build error:** `pip install -r requirements.txt` failed while building scikit-learn.
  Fix: use Python 3.12 and a fresh `.venv`, which has ready-made wheels.
- **bcrypt and passlib:** `AttributeError: module 'bcrypt' has no attribute '__about__'` appeared at registration.
  Fix: pin `bcrypt==4.0.1` in `requirements.txt`.
- **`.env` was required after the secret was moved out of the code:** tests set a test secret in `tests/conftest.py`, so they run without a `.env`.
- **Slow tests:** every test registers users and bcrypt hashing is slow on purpose, so the full run takes a few minutes.