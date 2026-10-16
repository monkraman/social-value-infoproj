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
    raw_prompt: Optional[str] = Field(default=None, description="Raw user prompt string")


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
    # Granular operational metrics matching client requirement
    sessions_per_year: Optional[float] = Field(default=None, description="Number of sessions per year")
    hours_per_session: Optional[float] = Field(default=None, description="Hours per delivery session")
    participants_per_session: Optional[float] = Field(default=None, description="Participants per session")
    indicative_cost_gbp: Optional[float] = Field(default=0.0, description="Estimated internal delivery cost to Infosys")
    commercial_viability: Optional[str] = Field(default="Zero-Cost Internal Volunteering", description="Cost structure tier")


class GovernanceCadence(BaseModel):
    social_value_lead: str = Field(
        default="Dedicated Infosys Social Value Lead assigned upon contract award",
        description="Lead role responsibility"
    )
    kickoff_cadence: str = Field(
        default="Joint Social Value Kick-Off Meeting held within 60 days of contract signature",
        description="Initial mobilization meeting"
    )
    reporting_frequency: str = Field(
        default="Quarterly Social Value Progress and KPIs performance reporting",
        description="Reporting cadence"
    )
    annual_review: str = Field(
        default="Annual SVROI impact evaluation and National TOMs financial reconciliation",
        description="Annual governance cycle"
    )


class SocialValuePackage(BaseModel):
    name: str
    initiatives: List[InitiativeItem] = Field(default_factory=list)
    rationale: str
    expected_impact: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    financial_calculation: Optional[PackageCalculation] = None
    indicative_delivery_cost_gbp: float = Field(default=0.0, description="Estimated total cost to Infosys to deliver this package")
    commercial_viability_summary: str = Field(default="Highly Viable / High SVROI", description="Commercial assessment")
    governance: GovernanceCadence = Field(default_factory=GovernanceCadence, description="Standardized governance framework")


class AIReasoningStep(BaseModel):
    step_number: int
    title: str
    detail: str
    status: str = "completed"


class ResponseGenerationResult(BaseModel):
    opportunity: Dict[str, Any]
    core_package: SocialValuePackage
    enhanced_package: SocialValuePackage
    localised_package: SocialValuePackage
    assumptions: List[str] = Field(default_factory=list)
    validation_required: List[str] = Field(default_factory=list)
    retrieved_evidence_chunks: int = 0
    grounding_summary: Dict[str, Any] = Field(default_factory=dict)
    ai_reasoning_chain: List[AIReasoningStep] = Field(default_factory=list, description="Transparent AI reasoning & evidence grounding chain")
    is_mock: bool = False


class PromptSubmissionRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Natural language tender specification or query")
    user_id: Optional[str] = Field(default=None, description="Optional user ID for audit logging")


class PromptSubmissionResponse(BaseModel):
    prompt_id: str
    is_rfp_prompt: bool
    intent: str
    explanation: Optional[str] = None
    request: Optional[Dict[str, Any]] = None
    result: Optional[ResponseGenerationResult] = None
    created_at: str


class PromptHistoryItem(BaseModel):
    id: str
    raw_prompt: str
    intent: str
    is_rfp_prompt: bool
    client_name: Optional[str] = None
    location: Optional[str] = None
    contract_value_gbp: Optional[float] = None
    duration_years: Optional[int] = None
    weighting_percent: Optional[float] = None
    priorities: List[str] = Field(default_factory=list)
    explanation: Optional[str] = None
    response_summary: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None


