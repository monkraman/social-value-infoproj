from app.api.health import router as health_router
from app.api.ai import router as ai_router
from app.api.documents import router as documents_router
from app.api.search import router as search_router
from app.api.responses import router as responses_router
from app.api.calculations import router as calculations_router

__all__ = [
    "health_router",
    "ai_router",
    "documents_router",
    "search_router",
    "responses_router",
    "calculations_router"
]
