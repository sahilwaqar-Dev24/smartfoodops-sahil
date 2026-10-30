# Engineering Notes and Decision Log - SmartFoodOps

Handwritten technical notes, architectural tradeoffs, and issue debugging logs recorded during the development of SmartFoodOps.

---

## 1. Module Development Progress

| Module | Scope / Domain | Status | Observations & Notes |
| :--- | :--- | :--- | :--- |
| **Module 1** | Foundation & Project Setup | Completed | Established clean layered directory hierarchy, SQLite connection, base configuration, and `/health` route. |
| **Module 2** | Authentication & RBAC | Completed | Integrated JWT bearer tokens using Passlib and bcrypt. Added registration and login for `customer`, `restaurant_admin`, and `rider`. |
| **Module 3** | Restaurants & Catalogs | Completed | Implemented multi-tenant restaurants, categories, menu items CRUD, stock tracking, and owner validation guards. |
| **Module 4** | Orders & State Machine | Completed | Built dynamic server-side total price calculations, sequential status machine (`PLACED` -> `READY`), and 409 Conflict jump guards. |
| **Module 5** | Rider Dispatch & Delivery | Completed | Added rider `is_available` toggle, automated dispatch, and full delivery state lifecycle (`PICKED_UP` -> `DELIVERED`). |
| **Module 6** | Analytics & TF-IDF Search | Completed | Platform and restaurant sales aggregation queries, plus scikit-learn TF-IDF Vectorizer and cosine similarity search. |
| **Module 7** | Testing & Seeding | Completed | Implemented 12 automated pytest cases with an in-memory SQLite fixture and an idempotent `seed.py` data script. |

---

## 2. Technical Decisions & Bug Fixes

### Python 3.14 Build Tools Failure
- **Issue**: Running `pip install -r requirements.txt` on global Python 3.14 threw C++ build compiler errors when compiling wheels for scikit-learn.
- **Fix**: Targeted the locally available Python 3.12 (64-bit) installation and generated a clean `.venv` environment to use stable pre-built binary wheels.

### Bcrypt 5.x & Passlib Incompatibility
- **Issue**: Encountered `AttributeError: module 'bcrypt' has no attribute '__about__'` during user registration testing.
- **Fix**: The latest passlib version requires an older bcrypt version. Pinned `bcrypt==4.0.1` inside `requirements.txt` to eliminate the regression.

### Server-Side Price Verification
- **Decision**: Client payloads only supply menu item IDs and quantities. The backend fetches authoritative prices directly from the `menu_items` table at order creation to completely prevent client-side price tampering.

### Strict State-Machine Transitions
- **Decision**: Forced orders to follow a strict linear progression (`PLACED` -> `ACCEPTED` -> `PREPARING` -> `READY` -> `ASSIGNED` -> `PICKED_UP` -> `DELIVERED`). Skipping steps or invalid transitions returns an explicit HTTP `409 Conflict`. All transitions are recorded in `order_status_history`.

### TF-IDF Search Cutoff Threshold
- **Decision**: Filtered TF-IDF vector similarity results with a minimum cosine similarity threshold of `0.05` so that completely irrelevant menu queries return an empty list rather than weak matches.