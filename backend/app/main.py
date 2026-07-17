"""
Smart Remote Interview System (SRIS) - Main Application
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.config import settings
from app.database import engine, Base
from app.api.router import api_router

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
async def health_check():
    return {"status": "healthy"}
