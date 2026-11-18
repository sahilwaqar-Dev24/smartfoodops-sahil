import logging
import uuid
from fastapi import FastAPI, Request
from app.core.config import settings
from app.core.logging_config import setup_logging
from app.api.health import router as health_router
from app.api.auth import router as auth_router
from app.api.restaurants import router as restaurants_router
from app.api.orders import router as orders_router
from app.api.riders import router as riders_router
from app.api.notifications import router as notifications_router
from app.api.analytics import router as analytics_router
from app.api.assistant import router as assistant_router
from app.db.session import engine, Base
import app.models  # saare models register karta hai (notifications table bhi)

setup_logging()
logger = logging.getLogger("smartfoodops.requests")

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="SmartFoodOps - Core Food Ordering Backend API"
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = uuid.uuid4().hex[:8]
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("request_id=%s %s %s crashed", request_id, request.method, request.url.path)
        raise
    logger.info(
        "request_id=%s %s %s -> %s",
        request_id, request.method, request.url.path, response.status_code
    )
    response.headers["X-Request-ID"] = request_id
    return response


# Include Routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(restaurants_router)
app.include_router(orders_router)
app.include_router(riders_router)
app.include_router(notifications_router)
app.include_router(analytics_router)
app.include_router(assistant_router)


@app.get("/")
def root():
    return {"message": "Welcome to SmartFoodOps Backend API. Visit /docs for Swagger UI."}