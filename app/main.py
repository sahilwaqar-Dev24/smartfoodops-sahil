from fastapi import FastAPI
from app.core.config import settings
from app.db.session import engine, Base
from app.api.health import router as health_router
from app.api.auth import router as auth_router
from app.api.restaurants import router as restaurant_router

# Database tables auto create karne ke liye
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="SmartFoodOps - Core Food Ordering Backend API"
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(restaurant_router)


@app.get("/")
def root():
    return {"message": "Welcome to SmartFoodOps Backend API. Visit /docs for Swagger UI."}