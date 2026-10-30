from fastapi import FastAPI
from app.core.config import settings
from app.api.health import router as health_router
from app.api.auth import router as auth_router
from app.api.restaurants import router as restaurants_router
from app.api.orders import router as orders_router
from app.api.analytics import router as analytics_router
from app.api.assistant import router as assistant_router
from app.db.session import engine, Base

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="SmartFoodOps - Core Food Ordering Backend API"
)

# Include Routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(restaurants_router)
app.include_router(orders_router)
app.include_router(analytics_router)
app.include_router(assistant_router)


@app.get("/")
def root():
    return {"message": "Welcome to SmartFoodOps Backend API. Visit /docs for Swagger UI."}