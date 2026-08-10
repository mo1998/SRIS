"""
Smart Remote Interview System (SRIS) - Main Application
"""

import json
import logging
import os
import threading
import time
import uuid

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import engine, Base
from app.api.router import api_router

logger = logging.getLogger("sris.request")

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Permissions-Policy": "camera=(self), microphone=(self), geolocation=()",
}

# Create database tables
Base.metadata.create_all(bind=engine)


def _maintenance_loop(stop_event: threading.Event) -> None:
    """Periodically run invitation expiry sweep and reminders."""
    from app.services.maintenance_service import run_maintenance

    logger.info("Maintenance loop started (interval=%ss)", settings.MAINTENANCE_INTERVAL_SECONDS)
    while not stop_event.wait(settings.MAINTENANCE_INTERVAL_SECONDS):
        try:
            result = run_maintenance()
            logger.info("Maintenance run: %s", result)
        except Exception as e:
            logger.error("Maintenance run failed: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    maintenance_thread = None
    stop_event = threading.Event()
    if settings.MAINTENANCE_ENABLED:
        maintenance_thread = threading.Thread(
            target=_maintenance_loop, args=(stop_event,), daemon=True, name="maintenance"
        )
        maintenance_thread.start()
    yield
    stop_event.set()
    if maintenance_thread is not None:
        maintenance_thread.join(timeout=5)


app = FastAPI(
    title="Smart Remote Interview System",
    description="AI-powered remote interview platform with emotion detection and candidate evaluation",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_observability_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    start_time = time.perf_counter()

    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > settings.MAX_REQUEST_BODY_SIZE:
        response = JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content={"detail": "Request body exceeds maximum size"},
        )
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-Ms"] = "0"
        for header, value in SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        return response

    response = await call_next(request)

    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time-Ms"] = str(duration_ms)
    for header, value in SECURITY_HEADERS.items():
        response.headers.setdefault(header, value)

    logger.info(json.dumps({
        "event": "http_request",
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "status_code": response.status_code,
        "duration_ms": duration_ms,
    }))

    return response

# Include API routes
app.include_router(api_router, prefix="/api")

# Mount static files for uploads
os.makedirs("uploads/interviews", exist_ok=True)
os.makedirs("uploads/reports", exist_ok=True)
app.mount("/static", StaticFiles(directory="uploads"), name="static")

@app.get("/")
async def root():
    return {
        "message": "Smart Remote Interview System API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check(request: Request, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return {
        "status": "healthy",
        "request_id": request.headers.get("X-Request-ID"),
    }
