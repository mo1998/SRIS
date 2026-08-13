"""
Pre-interview system check endpoints.

Public, unauthenticated endpoints used by the candidate-facing system check
to measure latency and real download/upload throughput before an interview
session starts. They only transfer fixed, inert payloads and carry no state.
"""

import time

from fastapi import APIRouter, HTTPException, Query, Request, Response, status

router = APIRouter(tags=["System Check"])

MAX_DOWNLOAD_SIZE_MB = 20
CHUNK = b"0" * (1024 * 1024)


@router.get("/ping")
async def ping(response: Response):
    """Return a minimal payload for latency (RTT) measurement."""
    response.headers["Cache-Control"] = "no-store"
    return {"timestamp": time.time(), "server_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}


@router.get("/download")
async def download(
    size_mb: int = Query(5, ge=1, le=MAX_DOWNLOAD_SIZE_MB, description="Payload size in MB"),
    response: Response = None,
):
    """Return a known-size inert payload to measure download throughput."""
    if size_mb > MAX_DOWNLOAD_SIZE_MB:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="size_mb exceeds limit")

    total_bytes = size_mb * 1024 * 1024
    payload = (CHUNK * (size_mb + 1))[:total_bytes]
    response.headers["Content-Length"] = str(total_bytes)
    response.headers["Cache-Control"] = "no-store"
    return Response(content=payload, media_type="application/octet-stream")


@router.post("/upload")
async def upload(request: Request, response: Response):
    """Accept a request body and report its size to measure upload throughput."""
    body = await request.body()
    response.headers["Cache-Control"] = "no-store"
    return {"received_bytes": len(body)}