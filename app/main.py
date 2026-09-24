"""
FastAPI Main Application
Includes Global Exception Handlers, Standard JSON Envelopes, and Observability Middleware.
"""
import os
import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.database import init_db, SessionLocal
from app.services.patient_service import PatientService
from app.api.v1.patients import router as patients_router
from app.api.v1.voice import router as voice_router

# Configure Structured Logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s"
)
logger = logging.getLogger("CareCloudApp")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle hook: initializes database tables and seeds demo data."""
    logger.info("Initializing persistent database tables...")
    init_db()
    db = SessionLocal()
    try:
        PatientService.seed_demo_data_if_empty(db)
        logger.info("Database initialized successfully.")
    finally:
        db.close()
    yield
    logger.info("Application shutting down.")


app = FastAPI(
    title="CareCloud Voice AI — Patient Registration API",
    description="Production-grade REST Web Service for U.S. Patient Demographic Registration",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Observability & Request Logging Middleware
@app.middleware("http")
async def log_requests_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration_ms = round((time.time() - start_time) * 1000, 2)
    logger.info(
        f"{request.method} {request.url.path} -> Status: {response.status_code} ({duration_ms}ms)"
    )
    return response


# Global Exception Handlers for Unified JSON Envelope
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Transforms FastAPI / Pydantic validation errors into standard error envelope."""
    details = []
    for err in exc.errors():
        loc = " -> ".join(str(item) for item in err.get("loc", []) if item != "body")
        details.append({
            "field": loc or "body",
            "message": err.get("msg", "Validation error")
        })

    logger.warning(f"Validation failure on {request.url.path}: {details}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "data": None,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "One or more fields failed validation.",
                "details": details
            }
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Transforms HTTPExceptions into standard error envelope."""
    status_code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "UNPROCESSABLE_ENTITY",
        500: "INTERNAL_SERVER_ERROR"
    }
    error_code = status_code_map.get(exc.status_code, "ERROR")

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "data": None,
            "error": {
                "code": error_code,
                "message": exc.detail,
                "details": None
            }
        }
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Catches unhandled errors and returns consistent 500 error envelope."""
    logger.error(f"Unhandled error on {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "data": None,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected internal server error occurred.",
                "details": None
            }
        }
    )


# Mount Routes: Expose directly on /patients (matching assessment spec) and /api/v1/patients
app.include_router(patients_router)
app.include_router(patients_router, prefix="/api/v1")
app.include_router(voice_router)
app.include_router(voice_router, prefix="/api/v1")

# Mount Static Files & Serve Apple iOS Dashboard
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", tags=["Frontend"], summary="CareCloud Apple iOS Web App")
@app.get("/dashboard", tags=["Frontend"], summary="CareCloud Clinical Dashboard")
def serve_dashboard():
    """Serves the Apple iOS-styled CareCloud Clinical Dashboard."""
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file, media_type="text/html")
    return {"message": "CareCloud Voice AI Backend running."}


@app.get("/health", tags=["Health"])
def health_check():
    """Service liveness probe."""
    return {
        "status": "healthy",
        "service": "carecloud-voice-patient-registration",
        "timestamp": time.time()
    }
