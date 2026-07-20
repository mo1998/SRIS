"""
Smart Remote Interview System (SRIS) - Main Application
"""

import json
import logging
import os
import time
import uuid

from fastapi import FastAPI, Request
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

app = FastAPI(
    title="Smart Remote Interview System",
    description="AI-powered remote interview platform with emotion detection and candidate evaluation",
    version="1.0.0"
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
async def health_check(request: Request):
    return {
        "status": "healthy",
        "request_id": request.headers.get("X-Request-ID"),
    }
