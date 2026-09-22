from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.logging_store import get_dashboard_stats

router = APIRouter()


@router.get("/api/stats")
async def stats():
    return await get_dashboard_stats()


@router.get("/dashboard")
async def dashboard_page():
    return FileResponse("app/static/dashboard.html")
