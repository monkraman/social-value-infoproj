from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from app.schemas.calculation import PackageCalculation


class OpportunityRequest(BaseModel):
    contract_duration_years: int = Field(default=3, ge=1, le=10, description="Duration in years")
    contract_value_gbp: float = Field(default=10000000.0, gt=0, description="Total contract value in GBP")
    social_value_weighting_percent: float = Field(default=10.0, ge=0, le=100, description="Social value weighting %")
    client: str = Field(default="Example Council", description="Target client or public authority")
    location: str = Field(default="Birmingham", description="Geographic delivery region")
    priorities: List[str] = Field(
        default=["Digital Inclusion", "Youth Employment"],
        description="Priority Social Value themes"
    )
    top_k: int = Field(default=6, ge=1, le=20, description="Evidence chunks to retrieve")


class InitiativeItem(BaseModel):
    name: str = Field(..., description="Name of the initiative")
    theme: str = Field(..., description="Theme (e.g. Digital Inclusion, Youth Employment)")
    location: str = Field(..., description="Location focus (e.g. Birmingham, National)")
    description: str = Field(..., description="Actionable summary of delivery")
    delivery_mechanism: str = Field(..., description="How it is delivered (e.g. 4 workshops/yr)")
    target_beneficiaries: str = Field(..., description="Who benefits")
    annual_volume: float = Field(default=1.0, description="Estimated annual volume/count")
    toms_metric_code: Optional[str] = Field(None, description="Linked TOMs proxy code (e.g. NT8)")
    partner: Optional[str] = Field(None, description="Partner organization, if supported by evidence")
    evidence_source: str = Field(..., description="Source document or 'Model Recommended'")
    is_from_knowledge_base: bool = Field(default=False, description="True if grounded in retrieved knowledge")


class SocialValuePackage(BaseModel):
    name: str
    initiatives: List[InitiativeItem] = Field(default_factory=list)
    rationale: str
    expected_impact: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    financial_calculation: Optional[PackageCalculation] = None


class ResponseGenerationResult(BaseModel):
    opportunity: Dict[str, Any]
    core_package: SocialValuePackage
    enhanced_package: SocialValuePackage
    localised_package: SocialValuePackage
    assumptions: List[str] = Field(default_factory=list)
    validation_required: List[str] = Field(default_factory=list)
    retrieved_evidence_chunks: int = 0
    grounding_summary: Dict[str, Any] = Field(default_factory=dict)
    is_mock: bool = False
