# SmartFoodOps - Food Ordering and Delivery Backend API

## Overview
SmartFoodOps is a modular backend REST API built using FastAPI, SQLAlchemy, and SQLite. It handles the complete food delivery lifecycle, including role-based authentication, restaurant menu management, server-side pricing, order status state machine, rider dispatching, analytics, and TF-IDF menu search.

---

## Tech Stack
- **Language**: Python 3.12
- **Framework**: FastAPI + Uvicorn
- **Database & ORM**: SQLite + SQLAlchemy 2.0
- **Authentication**: JWT (python-jose) + Passlib (Bcrypt)
- **Search**: scikit-learn (TF-IDF Vectorizer + Cosine Similarity)
- **Testing**: Pytest + HTTPX

---

## Project Structure
```text
smartfoodops-sahil/
├── app/
│   ├── api/            # API route endpoints
│   ├── core/           # Configuration and JWT security
│   ├── db/             # Database session and SQLite setup
│   ├── models/         # SQLAlchemy database models
│   ├── schemas/        # Pydantic validation schemas
│   └── services/       # Business logic (pricing, order state machine, TF-IDF search)
├── tests/              # Automated pytest suite and fixtures
├── seed.py             # Database seed script for demo data
├── requirements.txt    # Project dependencies
├── .env.example        # Environment variables template
└── .gitignore          # Git ignore rules