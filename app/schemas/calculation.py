from typing import List, Optional
from pydantic import BaseModel, Field


class TOMsMetric(BaseModel):
    id: Optional[int] = None
    code: str = Field(..., description="TOMs proxy code (e.g. NT1, NT8, SV-CLIM-1)")
    name: str = Field(..., description="Metric title")
    theme: str = Field(..., description="Social Value theme (Work, Economy, Planet, Community)")
    outcome: Optional[str] = Field(default=None, description="Outcome / Policy Goal")
    unit: str = Field(..., description="Unit of measure (e.g., sessions, people, weeks, £ spend)")
    unit_value_gbp: float = Field(..., description="Proxy unit value in GBP")
    description: Optional[str] = Field(default="", description="Brief guidance on measurement")
    evidence_required: Optional[str] = Field(default="", description="Verification and audit evidence required")
    ppn_mapping: Optional[str] = Field(default="", description="UK Social Value Model (PPN 06/20 / MAC code)")
    source: Optional[str] = Field(default="National TOMs / NHS Contract Benchmark")
    is_synthetic: Optional[bool] = Field(default=False, description="Whether this is a synthetic or benchmark proxy")
    is_active: Optional[bool] = Field(default=True)

    model_config = {"from_attributes": True}


class TomsMetricCreate(BaseModel):
    code: str = Field(..., description="Unique TOMs code (e.g., NT1, NT25)")
    name: str = Field(..., description="Metric name")
    theme: str = Field(..., description="Work, Economy, Planet, Community")
    outcome: Optional[str] = Field(default=None)
    unit: str = Field(..., description="Measurement unit (e.g., weeks, hours, £ spend)")
    unit_value_gbp: float = Field(..., description="Proxy value in GBP")
    description: Optional[str] = Field(default="")
    evidence_required: Optional[str] = Field(default="")
    ppn_mapping: Optional[str] = Field(default="")
    source: Optional[str] = Field(default="National TOMs")


class TomsMetricUpdate(BaseModel):
    name: Optional[str] = None
    theme: Optional[str] = None
    outcome: Optional[str] = None
    unit: Optional[str] = None
    unit_value_gbp: Optional[float] = None
    description: Optional[str] = None
    evidence_required: Optional[str] = None
    ppn_mapping: Optional[str] = None
    source: Optional[str] = None
    is_active: Optional[bool] = None


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


class OpportunityRecommendRequest(BaseModel):
    industry: str = Field(default="IT Services", description="Bidder industry / service area")
    contract_value_gbp: float = Field(default=5000000.0, description="Total contract value in GBP")
    duration_years: int = Field(default=3, description="Contract duration in years")
    target_weighting_percent: float = Field(default=10.0, description="Target Social Value % (e.g., 10%)")
    location: Optional[str] = Field(default="UK National", description="Target delivery council / region")
    focus_areas: Optional[List[str]] = Field(
        default=None,
        description="Optional focus themes e.g. ['Work', 'Planet', 'Community', 'Economy', 'Modern Slavery']"
    )


class OpportunityRecommendationItem(BaseModel):
    toms_code: str
    initiative_name: str
    theme: str
    ppn_mac: str
    unit: str
    unit_value_gbp: float
    annual_volume: float
    duration_years: int
    total_volume: float
    total_social_value_gbp: float
    why_recommended: str
    delivery_approach: str
    evidence_needed: str


class OpportunityRecommendResponse(BaseModel):
    contract_value_gbp: float
    duration_years: int
    target_weighting_percent: float
    target_social_value_gbp: float
    total_recommended_social_value_gbp: float
    achieved_weighting_percent: float
    target_met: bool
    recommendations: List[OpportunityRecommendationItem]
    executive_summary: str
