"""Super-administrators choose which AI provider answers first. Keys are never sent or accepted here."""
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.auth import require_roles
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.services import ai_settings_service as ai
from app.services.audit_service import AuditService

router = APIRouter(prefix="/admin/ai", tags=["AI provider"])

_superadmin = require_roles("superadmin")


class ProviderChoice(BaseModel):
    # "default" clears the choice and follows the deployment's own order (LLM_PROVIDER, LLM_FALLBACK).
    provider: Literal["azure", "gemini", "openai", "default"]


def _state(db: Session) -> dict:
    stored = ai.stored_primary(db)
    return {
        "providers": [
            {"id": p, "label": ai.provider_label(p), "model": ai.provider_model(p),
             "configured": settings._chat_configured(p)}
            for p in ai.PROVIDERS
        ],
        "selected": stored or "default",
        "default_order": settings.provider_order,
        "order": ai.effective_order(db),
        "embeddings": settings.embedding_provider,
    }


@router.get("")
def get_ai_settings(db: Session = Depends(get_db), _admin: User = Depends(_superadmin)):
    return _state(db)


@router.put("")
def set_ai_provider(choice: ProviderChoice, request: Request, db: Session = Depends(get_db),
                    admin: User = Depends(_superadmin)):
    target = None if choice.provider == "default" else choice.provider
    if target and not settings._chat_configured(target):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                            detail=f"{ai.provider_label(target)} has no key configured on the server.")
    before = ai.stored_primary(db) or "default"
    ai.set_primary(db, target, admin.email)
    AuditService.record_log(
        db,
        request_id=getattr(request.state, "request_id", None) or str(uuid.uuid4()),
        message=f"AI provider changed from {before} to {choice.provider} by {admin.email}",
        event_type="AI_PROVIDER_CHANGED",
        endpoint="/admin/ai",
        method="PUT",
        status_code=200,
        user_id=str(admin.id),
        metadata_payload={"from": before, "to": choice.provider},
    )
    return _state(db)
