from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.schemas.calculation import (
    TOMsMetric,
    TomsMetricCreate,
    TomsMetricUpdate,
    InitiativeCalculation,
    PackageCalculation,
    OpportunityRecommendRequest,
    OpportunityRecommendResponse
)
from app.services.calculation_service import calculation_service

router = APIRouter(prefix="/calculations", tags=["Deterministic Calculations & TOMs"])


class InitiativeCalcRequest(BaseModel):
    initiative_name: str = Field(default="Birmingham Digital Skills Clinic")
    toms_code: Optional[str] = Field(default="NT8")
    annual_volume: float = Field(default=4.0)
    duration_years: int = Field(default=3)


class PackageCalcRequest(BaseModel):
    package_name: str = Field(default="Sample Package")
    contract_value_gbp: float = Field(default=10000000.0)
    duration_years: int = Field(default=3)
    target_weighting_percent: float = Field(default=10.0)
    initiatives: List[InitiativeCalcRequest] = Field(default_factory=list)


@router.get("/metrics", response_model=List[TOMsMetric])
def list_toms_metrics(
    theme: Optional[str] = Query(None, description="Filter by theme e.g. Work, Planet, Community, Economy"),
    search: Optional[str] = Query(None, description="Search term for code, name, description"),
    active_only: bool = Query(False, description="Filter only active metrics"),
    db: Session = Depends(get_db)
):
    """
    Lists all National TOMs and NHS contract benchmark proxy metrics.
    Supports filtering and search.
    """
    return calculation_service.get_all_metrics(
        db=db,
        theme=theme,
        search=search,
        active_only=active_only
    )


@router.get("/metrics/{code}", response_model=TOMsMetric)
def get_toms_metric_by_code(code: str, db: Session = Depends(get_db)):
    """Fetch details for a specific TOMs metric by its code."""
    metric = calculation_service.get_metric_by_code(db=db, code=code)
    if not metric:
        raise HTTPException(status_code=404, detail=f"TOMs metric '{code}' not found")
    return metric


@router.post("/metrics", response_model=TOMsMetric, status_code=201)
def add_toms_metric(metric_in: TomsMetricCreate, db: Session = Depends(get_db)):
    """
    Add a new TOMs metric or contract-specific proxy into the verified database.
    """
    try:
        return calculation_service.create_metric(db=db, metric_in=metric_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add metric: {str(e)}")


@router.put("/metrics/{code}", response_model=TOMsMetric)
def configure_toms_metric(code: str, metric_in: TomsMetricUpdate, db: Session = Depends(get_db)):
    """
    Update or reconfigure an existing TOMs proxy metric in the database.
    """
    updated = calculation_service.update_metric(db=db, code=code, metric_in=metric_in)
    if not updated:
        raise HTTPException(status_code=404, detail=f"TOMs metric '{code}' not found")
    return updated


@router.delete("/metrics/{code}")
def delete_toms_metric(code: str, db: Session = Depends(get_db)):
    """Deactivate or remove a TOMs metric from the active catalog."""
    success = calculation_service.delete_metric(db=db, code=code)
    if not success:
        raise HTTPException(status_code=404, detail=f"TOMs metric '{code}' not found")
    return {"message": f"Metric '{code}' successfully deactivated"}


@router.post("/reset-defaults")
def restore_default_metrics(db: Session = Depends(get_db)):
    """Restore standard National TOMs + NHS benchmark catalog."""
    count = calculation_service.reset_to_defaults(db=db)
    return {"message": f"Successfully restored {count} verified TOMs & benchmark metrics."}


@router.post("/recommend", response_model=OpportunityRecommendResponse)
def recommend_opportunities(req: OpportunityRecommendRequest, db: Session = Depends(get_db)):
    """
    Intelligent Opportunity Finder for Document-less Clients:
    Generates balanced, winning Social Value commitments based on contract size,
    industry, and location without requiring existing company documents.
    """
    return calculation_service.recommend_opportunities(db=db, req=req)


@router.post("/initiative", response_model=InitiativeCalculation)
def calculate_single_initiative(req: InitiativeCalcRequest, db: Session = Depends(get_db)):
    """Deterministically calculates impact for a single initiative."""
    return calculation_service.calculate_initiative(
        initiative_name=req.initiative_name,
        toms_code=req.toms_code,
        annual_volume=req.annual_volume,
        duration_years=req.duration_years,
        db=db
    )


@router.post("/package", response_model=PackageCalculation)
def calculate_package(req: PackageCalcRequest, db: Session = Depends(get_db)):
    """Deterministically calculates total impact and contract percentage for a package."""
    items = [
        {
            "name": init.initiative_name,
            "toms_metric_code": init.toms_code,
            "annual_volume": init.annual_volume
        }
        for init in req.initiatives
    ]

    return calculation_service.calculate_package(
        package_name=req.package_name,
        initiatives=items,
        contract_value_gbp=req.contract_value_gbp,
        duration_years=req.duration_years,
        target_weighting_percent=req.target_weighting_percent,
        db=db
    )
