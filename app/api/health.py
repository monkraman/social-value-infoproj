from fastapi import APIRouter
from app.core.database import check_db_connection
from app.core.config import settings

router = APIRouter(tags=["Health"])


@router.get("/health")
def get_health():
    """
    Milestone 1: Health check endpoint.
    Returns status: ok along with system connectivity details.
    """
    db_status = check_db_connection()
    return {
        "status": "ok",
        "app_name": settings.APP_NAME,
        "database": db_status,
        "active_provider": settings.active_provider,
        "providers": {
            "gemini": {
                "configured": settings.is_gemini_configured,
                "model": settings.GEMINI_MODEL
            },
            "openai": {
                "configured": settings.is_openai_configured,
                "model": settings.OPENAI_CHAT_MODEL
            }
        },
        "embedding_dimension": settings.EMBEDDING_DIMENSION
    }
