"""Health check endpoint."""
from fastapi import APIRouter
from app.core.config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/health")
def health():
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": "1.0.0",
        "ai_configured": settings.ai_configured,
        "ai_provider": settings.ai_provider,
        "supabase_configured": bool(settings.supabase_url),
    }
