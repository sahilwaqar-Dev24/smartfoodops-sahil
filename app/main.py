from fastapi import FastAPI
from app.core.config import settings
from app.api.health import router as health_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="SmartFoodOps - Core Food Ordering Backend API"
)

app.include_router(health_router)

@app.get("/")
def root():
    return {"message": "Welcome to SmartFoodOps Backend API. Visit /docs for Swagger UI."}