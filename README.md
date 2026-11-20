# SmartFoodOps – Food Ordering & Delivery Backend

SmartFoodOps is a backend API for a small food ordering and delivery platform.
Customers browse restaurants and place orders, restaurant admins manage menus and
orders, and riders deliver them. It also includes simple analytics, a TF-IDF menu
search and a rule-based food assistant.

**Scope:** backend API only. Test it with Swagger UI (`/docs`), Postman or curl.

## Tech stack

| Area | Choice |
|------|--------|
| Language | Python 3.11+ (developed on 3.12) |
| API | FastAPI + Pydantic |
| Database | SQLite + SQLAlchemy |
| Auth | JWT (python-jose) + bcrypt password hashing |
| Search | scikit-learn TF-IDF + cosine similarity |
| Tests | pytest + FastAPI TestClient (httpx) |

## Setup

1. **Create a virtual environment and install packages**

   Windows (PowerShell):
   ```
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
   macOS / Linux:
   ```
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Create the `.env` file** (secrets are never committed). Copy `.env.example`
   to `.env` and put a random secret in it. This command writes a new `.env` for you:

   Windows (PowerShell):
   ```
   python -c "import secrets; print('JWT_SECRET=' + secrets.token_hex(32))" | Out-File -Encoding ascii .env
   ```
   macOS / Linux:
   ```
   python3 -c "import secrets; print('JWT_SECRET=' + secrets.token_hex(32))" > .env
   ```
   `JWT_SECRET` is required (at least 16 characters). The app will not start without it.

3. **Load demo data**
   ```
   python seed.py
   ```
   The seed script is safe to run again (it does not create duplicates).
   To start from scratch, delete `smartfoodops.db` and run it again.

## Run

```
uvicorn app.main:app --reload
```

- Swagger UI: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health

In Swagger UI click **Authorize** and log in with an email and password from the table below.

## Demo accounts (created by `seed.py`)

Password for every account: `Password123!`

| Role | Email |
|------|-------|
| Restaurant admin (KFC Abbottabad) | admin_kfc@smartfoodops.com |
| Restaurant admin (Desi Kitchen, Chapli Kebab Corner) | admin_desi@smartfoodops.com |
| Rider | kamran_rider@smartfoodops.com, ali_rider@smartfoodops.com |
| Customer | customer1@smartfoodops.com, customer2@smartfoodops.com |

The seed data also has one **closed** restaurant, one **unavailable** menu item, one item with
**low stock** (Pepsi, stock 3) and four old orders so the analytics endpoints show numbers.
A step by step demo is in [docs/demo_script.md](docs/demo_script.md).

## Run the tests

```
python -m pytest -q
python -m pytest -q --cov=app
```

There are 95 tests (about 96% coverage). They use an in-memory SQLite database, so they
never touch `smartfoodops.db`, and they do not need a `.env` file. The full run takes
1 to 3 minutes because every test registers users and hashes passwords.

## Main endpoints

| Area | Method and path | Who can use it |
|------|-----------------|----------------|
| Health | `GET /health` | anyone |
| Auth | `POST /auth/register`, `POST /auth/login` | anyone |
| Profile | `GET /users/me` (also `GET /auth/me`) | logged-in user |
| Restaurants | `GET /restaurants/?name=&cuisine=&limit=&offset=` | anyone (open restaurants only) |
| | `POST /restaurants/`, `GET /restaurants/mine`, `PATCH /restaurants/{id}` | restaurant admin (own restaurants) |
| Menu | `POST/GET /restaurants/{id}/categories`, `PATCH/DELETE /restaurants/categories/{id}` | admin writes, anyone reads |
| | `POST/GET /restaurants/categories/{id}/items`, `PATCH/DELETE /restaurants/items/{id}` | admin writes, anyone reads available items |
| | `GET /restaurants/categories/{id}/all-items` | owner (includes unavailable items) |
| Orders | `POST /orders/` | customer |
| | `GET /orders/`, `GET /orders/{id}`, `GET /orders/{id}/history` | customer, restaurant admin or rider involved in the order |
| | `POST /orders/{id}/accept`, `POST /orders/{id}/reject` | admin of that restaurant |
| | `PATCH /orders/{id}/status` | role depends on the status (see below) |
| | `POST /orders/{id}/assign-rider` | admin of that restaurant |
| Riders | `GET /riders/available`, `PATCH /riders/me/availability` | admin / rider |
| Notifications | `GET /notifications/` | logged-in user (own notifications) |
| Analytics | `GET /analytics/platform`, `GET /analytics/orders-per-restaurant`, `GET /analytics/restaurants/{id}` (`?date_from=&date_to=`) | restaurant admin (own restaurants only) |
| Search | `GET /search/menu-items?q=spicy chicken under 500&cuisine=&max_price=&top_k=` | anyone |
| Assistant | `POST /assistant/recommend` | anyone |

## Order status flow

```
PLACED -> ACCEPTED -> PREPARING -> READY -> ASSIGNED -> PICKED_UP -> DELIVERED
   |
   +-> REJECTED            (a cancel is also possible from any state before PICKED_UP)
```

An invalid jump (for example `PLACED` to `DELIVERED`) returns **409 Conflict**.
More details are in [docs/design.md](docs/design.md).

## Error format

Every error uses the same JSON shape and never shows stack traces or database errors:

```json
{"error": {"status_code": 404, "message": "Order not found"}}
```

Validation errors (422) also include a `details` list with the field names.

## Project structure

```
app/
  main.py          app setup, middleware, routers
  api/             routes only (thin): auth, users, restaurants, orders, riders,
                   notifications, analytics, search, assistant, health
  services/        business rules: auth, restaurant, order, notification, analytics, search
  models/          SQLAlchemy tables
  schemas/         Pydantic request/response models
  core/            config, security (JWT, hashing), errors, logging
  db/              database session
tests/             95 pytest tests
docs/              design.md, ERD.md, PRD.md, demo_script.md
seed.py            demo data
```

## More documentation

- [docs/design.md](docs/design.md): architecture, status flow, rider rule, design decisions
- [docs/ERD.md](docs/ERD.md): database diagram
- [docs/PRD.md](docs/PRD.md): users, use cases, requirements, weekly milestones
- [docs/demo_script.md](docs/demo_script.md): demo steps
- [NOTES.md](NOTES.md): progress tracker and problems solved

## Known limits

- Rider assignment is "first available rider". It does not handle two requests at the same
  millisecond (locking is outside the scope of this edition).
- SQLite is used for simplicity. There are no Alembic migrations and no Docker setup.
- There is no separate platform admin role. A restaurant admin sees analytics only for their own restaurants.