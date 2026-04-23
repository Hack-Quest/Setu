from fastapi import APIRouter
from database.ngos_db import get_dashboard_stats

router = APIRouter()

@router.get("/stats")
def get_stats():
    return get_dashboard_stats()