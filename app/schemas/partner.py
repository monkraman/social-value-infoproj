from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class RegionalPartnerBase(BaseModel):
    location: str = Field(..., description="City or region (e.g. Birmingham, Manchester, National)")
    partner_name: str = Field(..., description="Organization name")
    theme: str = Field(..., description="Social Value theme (Work, Planet, Community, Economy, Modern Slavery)")
    toms_code: Optional[str] = Field(default=None, description="Mapped TOMs metric code (e.g. NT1, NT8)")
    focus_area: Optional[str] = Field(default=None, description="Initiative focus (e.g. Youth Employment)")
    contact_info: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    is_approved: bool = Field(default=True)


class RegionalPartnerCreate(RegionalPartnerBase):
    pass


class RegionalPartnerUpdate(BaseModel):
    location: Optional[str] = None
    partner_name: Optional[str] = None
    theme: Optional[str] = None
    toms_code: Optional[str] = None
    focus_area: Optional[str] = None
    contact_info: Optional[str] = None
    description: Optional[str] = None
    is_approved: Optional[bool] = None


class RegionalPartnerResponse(RegionalPartnerBase):
    id: int
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

