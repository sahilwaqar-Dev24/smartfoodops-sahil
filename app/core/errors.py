import logging
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("smartfoodops.errors")


def error_response(status_code: int, message: str, details=None, headers=None) -> JSONResponse:
    """Har error ka ek jaisa JSON format:
    {"error": {"status_code": 404, "message": "...", "details": [...]}}
    """
    body = {"error": {"status_code": status_code, "message": message}}
    if details:
        body["error"]["details"] = details
    return JSONResponse(status_code=status_code, content=body, headers=headers)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        # FastAPI ka HTTPException bhi isi mein aata hai (404, 403, 409, ...)
        return error_response(exc.status_code, str(exc.detail), headers=getattr(exc, "headers", None))

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        # Sirf field ka naam aur message bhejte hain, user ka input (jaise password) wapas nahi
        details = [
            {
                "field": ".".join(str(part) for part in err["loc"][1:]) or str(err["loc"][0]),
                "message": err["msg"],
            }
            for err in exc.errors()
        ]
        return error_response(422, "Validation failed", details=details)

    @app.exception_handler(SQLAlchemyError)
    async def database_exception_handler(request: Request, exc: SQLAlchemyError):
        logger.exception("database_error %s %s", request.method, request.url.path)
        return error_response(500, "A database error occurred. Please try again later")

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        # Traceback sirf log mein jata hai, client ko nahi
        logger.exception("unhandled_error %s %s", request.method, request.url.path)
        return error_response(500, "Internal server error")