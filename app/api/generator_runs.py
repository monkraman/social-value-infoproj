"""Saved Initiative Generator runs: the user's own history.

Every run belongs to the user who saved it. Other users, administrators included, cannot
list, open, change or delete it; a run that is not yours answers 404, so ids reveal nothing.
"""
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.database import get_db
from app.models.generator_run import GeneratorRun
from app.models.user import User

router = APIRouter(prefix="/generator/runs", tags=["Initiative Generator history"])

# A saved screen is a few hundred KB at most; anything far larger is a mistake or abuse.
MAX_STATE_BYTES = 2_000_000


class RunIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    client: Optional[str] = Field(default=None, max_length=255)
    region: Optional[str] = Field(default=None, max_length=100)
    framework: Optional[str] = Field(default=None, max_length=20)
    contract_value_gbp: Optional[float] = Field(default=None, ge=0)
    target_gbp: Optional[float] = Field(default=None, ge=0)
    value_gbp: Optional[float] = Field(default=None, ge=0)
    initiative_count: int = Field(default=0, ge=0, le=1000)
    state: Dict[str, Any]

    @field_validator("title", "client")
    @classmethod
    def _strip(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() or None if v is not None else None

    @field_validator("state")
    @classmethod
    def _size(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        if len(json.dumps(v, default=str)) > MAX_STATE_BYTES:
            raise ValueError("Saved run is too large")
        return v


class RunSummary(BaseModel):
    id: str
    title: str
    client: Optional[str]
    region: Optional[str]
    framework: Optional[str]
    contract_value_gbp: Optional[float]
    target_gbp: Optional[float]
    value_gbp: Optional[float]
    initiative_count: int
    created_at: datetime
    updated_at: datetime


class RunDetail(RunSummary):
    state: Dict[str, Any]


def _summary(run: GeneratorRun) -> Dict[str, Any]:
    return {
        "id": str(run.id), "title": run.title, "client": run.client, "region": run.region,
        "framework": run.framework, "contract_value_gbp": run.contract_value_gbp,
        "target_gbp": run.target_gbp, "value_gbp": run.value_gbp,
        "initiative_count": run.initiative_count, "created_at": run.created_at, "updated_at": run.updated_at,
    }


def _own_run(run_id: str, user: User, db: Session) -> GeneratorRun:
    try:
        rid = uuid.UUID(run_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    run = db.query(GeneratorRun).filter(GeneratorRun.id == rid, GeneratorRun.user_id == user.id).first()
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return run


def _apply(run: GeneratorRun, body: RunIn) -> None:
    title = body.title or "Untitled tender"
    run.title, run.client, run.region, run.framework = title, body.client, body.region, body.framework
    run.contract_value_gbp, run.target_gbp, run.value_gbp = body.contract_value_gbp, body.target_gbp, body.value_gbp
    run.initiative_count, run.state = body.initiative_count, body.state


@router.get("", response_model=List[RunSummary])
def list_runs(
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """The signed-in user's saved runs, most recently changed first."""
    runs = (
        db.query(GeneratorRun)
        .filter(GeneratorRun.user_id == user.id)
        .order_by(GeneratorRun.updated_at.desc())
        .limit(limit)
        .all()
    )
    return [_summary(r) for r in runs]


@router.post("", response_model=RunSummary, status_code=status.HTTP_201_CREATED)
def create_run(body: RunIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    run = GeneratorRun(user_id=user.id)
    _apply(run, body)
    db.add(run)
    db.commit()
    db.refresh(run)
    return _summary(run)


@router.get("/{run_id}", response_model=RunDetail)
def get_run(run_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    run = _own_run(run_id, user, db)
    return {**_summary(run), "state": run.state}


@router.put("/{run_id}", response_model=RunSummary)
def update_run(run_id: str, body: RunIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    run = _own_run(run_id, user, db)
    _apply(run, body)
    db.commit()
    db.refresh(run)
    return _summary(run)


@router.delete("/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_run(run_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    run = _own_run(run_id, user, db)
    db.delete(run)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
