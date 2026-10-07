from typing import List, Optional
from pydantic import BaseModel, Field


class TOMsMetric(BaseModel):
    code: str = Field(..., description="TOMs proxy code (e.g. NT1, NT8)")
    name: str = Field(..., description="Metric title")
    theme: str = Field(..., description="Social Value theme")
    unit: str = Field(..., description="Unit of measure (e.g., sessions, people, weeks)")
    unit_value_gbp: float = Field(..., description="Proxy unit value in GBP")
    description: str = Field(..., description="Brief guidance on measurement")
    is_synthetic: bool = Field(default=True, description="Always flagged for synthetic POC values")


class InitiativeCalculation(BaseModel):
    initiative_name: str
    toms_code: str
    metric_name: str
    unit: str
    unit_value_gbp: float
    annual_volume: float
    duration_years: int
    total_volume: float
    total_social_value_gbp: float
    calculation_formula: str


class PackageCalculation(BaseModel):
    package_name: str
    initiatives: List[InitiativeCalculation] = Field(default_factory=list)
    total_social_value_gbp: float = 0.0
    contract_value_gbp: float
    social_value_percentage: float = 0.0
    target_weighting_percent: float
    target_social_value_gbp: float
    target_met: bool = False
    audit_trail: List[str] = Field(default_factory=list)
