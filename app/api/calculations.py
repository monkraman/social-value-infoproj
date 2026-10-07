from typing import List, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.schemas.calculation import TOMsMetric, InitiativeCalculation, PackageCalculation
from app.services.calculation_service import calculation_service

router = APIRouter(prefix="/calculations", tags=["Deterministic Calculations"])


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
def list_toms_metrics():
    """Lists all synthetic National TOMs proxy metrics with unit values."""
    return calculation_service.get_all_metrics()


@router.post("/initiative", response_model=InitiativeCalculation)
def calculate_single_initiative(req: InitiativeCalcRequest):
    """Deterministically calculates impact for a single initiative."""
    return calculation_service.calculate_initiative(
        initiative_name=req.initiative_name,
        toms_code=req.toms_code,
        annual_volume=req.annual_volume,
        duration_years=req.duration_years
    )


@router.post("/package", response_model=PackageCalculation)
def calculate_package(req: PackageCalcRequest):
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
        target_weighting_percent=req.target_weighting_percent
    )
