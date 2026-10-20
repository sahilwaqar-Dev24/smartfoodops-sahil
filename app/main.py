from fastapi import FastAPI
from app.core.config import settings
from app.db.session import engine, Base
from app.models.user import User  # Table metadata register karne ke liye
from app.api.health import router as health_router
from app.api.auth import router as auth_router

# Database tables automatically create karne ke liye
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="SmartFoodOps - Core Food Ordering Backend API"
)

# Routers include karna
app.include_router(health_router)
app.include_router(auth_router)

@app.get("/")
def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME} API",
        "docs": "/docs"
    }