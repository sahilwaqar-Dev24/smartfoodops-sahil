from fastapi import FastAPI
from app.core.config import settings
from app.db.session import engine, Base
import app.models  # Database tables register karne ke liye
from app.api.health import router as health_router
from app.api.auth import router as auth_router
from app.api.restaurants import router as restaurants_router
from app.api.orders import router as orders_router

# Server startup par tables create karna
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="SmartFoodOps - Core Food Ordering Backend API"
)

# Routers include karna
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(restaurants_router)
app.include_router(orders_router)


@app.get("/")
def root():
    return {"message": "Welcome to SmartFoodOps Backend API. Visit /docs for Swagger UI."}