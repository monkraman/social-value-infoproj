from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.partner import RegionalPartner as RegionalPartnerModel
from app.core.database import Base, engine
from app.schemas.partner import RegionalPartnerCreate, RegionalPartnerUpdate, RegionalPartnerResponse

DEFAULT_PARTNERS_DATA: List[Dict[str, Any]] = [
    # Birmingham & West Midlands
    {
        "location": "Birmingham",
        "partner_name": "BMet College & West Midlands Apprenticeship Hub",
        "theme": "Work",
        "toms_code": "NT1",
        "focus_area": "Accredited Level 3/4 Tech Apprenticeships",
        "description": "Leading further education college delivering local apprenticeship placements across Birmingham."
    },
    {
        "location": "Birmingham",
        "partner_name": "St Basils Youth Charity",
        "theme": "Work",
        "toms_code": "NT3",
        "focus_area": "Young People (16-24 NEET) Career Coaching",
        "description": "Specialist youth charity supporting vulnerable young people and NEETs into sustained employment."
    },
    {
        "location": "Birmingham",
        "partner_name": "Birmingham Community Matters & West Midlands Digital Device Bank",
        "theme": "Community",
        "toms_code": "NT8",
        "focus_area": "Community Digital Inclusion Workshops",
        "description": "Grassroots network hosting digital literacy clinics and broadband access support."
    },
    {
        "location": "Birmingham",
        "partner_name": "West Midlands Chamber of Commerce & WMCA SME Network",
        "theme": "Economy",
        "toms_code": "NT14",
        "focus_area": "Local SME & VCSE Supply Chain Integration",
        "description": "Regional business network promoting tier-2 supply chain spending and prompt payments."
    },

    # Manchester & North West
    {
        "location": "Manchester",
        "partner_name": "Manchester Metropolitan / The Manchester College",
        "theme": "Work",
        "toms_code": "NT1",
        "focus_area": "Cloud & Software Engineering Apprenticeships",
        "description": "Regional education anchor supporting youth tech careers across Greater Manchester."
    },
    {
        "location": "Manchester",
        "partner_name": "Manchester Youth Zone & HideOut Youth Zone",
        "theme": "Work",
        "toms_code": "NT3",
        "focus_area": "Youth Employability & Mentoring Programmes",
        "description": "State-of-the-art youth facilities delivering work-readiness clubs and mentoring in high-deprivation wards."
    },
    {
        "location": "Manchester",
        "partner_name": "Greater Manchester Digital Inclusion Coalition",
        "theme": "Community",
        "toms_code": "NT8",
        "focus_area": "Digital Literacy & Community Hubs",
        "description": "Place-based coalition addressing digital exclusion across Manchester and Salford."
    },
    {
        "location": "Manchester",
        "partner_name": "Greater Manchester Chamber of Commerce",
        "theme": "Economy",
        "toms_code": "NT14",
        "focus_area": "Regional SME Diversity & Procurement Spend",
        "description": "Largest UK chamber connecting contract procurement with local verified suppliers."
    },

    # London
    {
        "location": "London",
        "partner_name": "London South Bank Apprenticeships Hub",
        "theme": "Work",
        "toms_code": "NT1",
        "focus_area": "Tech Apprenticeships for Diverse Cohorts",
        "description": "South London university partner specializing in widening participation into tech."
    },
    {
        "location": "London",
        "partner_name": "Mayor's Fund for London / London Youth",
        "theme": "Work",
        "toms_code": "NT3",
        "focus_area": "Social Mobility & NEET Mentoring",
        "description": "Charity dedicated to empowering young Londoners from low-income backgrounds."
    },
    {
        "location": "London",
        "partner_name": "Good Things Foundation & London Digital Inclusion Network",
        "theme": "Community",
        "toms_code": "NT8",
        "focus_area": "National Databank & Device Distribution",
        "description": "Leading digital inclusion charity delivering Learn My Way modules and mobile data connectivity."
    },
    {
        "location": "London",
        "partner_name": "London Chamber of Commerce & Industry (LCCI)",
        "theme": "Economy",
        "toms_code": "NT14",
        "focus_area": "Local SME & Social Enterprise Supply Chains",
        "description": "Connecting major tier-1 contractors with borough-level micro-businesses."
    },

    # Leeds & Yorkshire
    {
        "location": "Leeds",
        "partner_name": "Leeds City College Apprenticeship Hub",
        "theme": "Work",
        "toms_code": "NT1",
        "focus_area": "Digital Skills & Software Apprenticeships",
        "description": "Accredited training provider supporting Yorkshire technology apprentices."
    },
    {
        "location": "Leeds",
        "partner_name": "100% Digital Leeds & Solidaritech",
        "theme": "Community",
        "toms_code": "NT8",
        "focus_area": "Hardware Refurbishment & Digital Equity",
        "description": "Council-backed initiative ensuring all residents have digital access and confidence."
    },

    # National UK / NHS Framework Partners
    {
        "location": "National UK",
        "partner_name": "QA Consulting / FWS Academy",
        "theme": "Work",
        "toms_code": "NHS-SV2-01",
        "focus_area": "Level 3/4 Azure Cloud & Digital Ambassador Academy",
        "description": "Nationwide accredited training provider delivering structured apprenticeships (Schedule 8 Annex 6)."
    },
    {
        "location": "National UK",
        "partner_name": "Good Things Foundation",
        "theme": "Community",
        "toms_code": "NHS-SV2-02",
        "focus_area": "Device Prescribing & National Device Bank",
        "description": "Partner delivering device prescribing and National Databank connectivity packages across GP practices."
    },
    {
        "location": "National UK",
        "partner_name": "Centre for Sustainable Healthcare (CSH)",
        "theme": "Planet",
        "toms_code": "NHS-SV1-02",
        "focus_area": "Green Health Routes & NHS Forest Biodiversity",
        "description": "Environmental non-profit leading nature-based health routes and healthcare sustainability."
    },
    {
        "location": "National UK",
        "partner_name": "Unseen UK",
        "theme": "Modern Slavery",
        "toms_code": "NHS-SV3-02",
        "focus_area": "Clinical Modern Slavery Detection & Supply Chain Training",
        "description": "UK leading modern slavery charity providing healthcare detection courses and victim support."
    },
    {
        "location": "National UK",
        "partner_name": "New Futures Network & Jobcentre Plus",
        "theme": "Work",
        "toms_code": "NHS-SV2-03",
        "focus_area": "E-Waste Hardware Refurbishment for Prison Leavers",
        "description": "Ministry of Justice employment pipeline training ex-offenders in certified IT asset disposal."
    }
]


class PartnerService:
    def ensure_seeded(self, db: Session) -> None:
        try:
            Base.metadata.create_all(bind=engine)
            count = db.query(RegionalPartnerModel).count()
            if count == 0:
                for item in DEFAULT_PARTNERS_DATA:
                    db.add(RegionalPartnerModel(**item))
                db.commit()
        except Exception as e:
            db.rollback()
            print(f"[PartnerService Warning] Seeding check deferred: {e}")

    def list_partners(
        self,
        db: Session,
        location: Optional[str] = None,
        theme: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[RegionalPartnerResponse]:
        self.ensure_seeded(db)
        query = db.query(RegionalPartnerModel)

        if location and location.lower() != "all":
            query = query.filter(RegionalPartnerModel.location.ilike(f"%{location.strip()}%"))
        if theme and theme.lower() != "all":
            query = query.filter(RegionalPartnerModel.theme.ilike(f"%{theme.strip()}%"))
        if search:
            q = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    RegionalPartnerModel.partner_name.ilike(q),
                    RegionalPartnerModel.location.ilike(q),
                    RegionalPartnerModel.focus_area.ilike(q),
                    RegionalPartnerModel.toms_code.ilike(q)
                )
            )

        rows = query.order_by(RegionalPartnerModel.location.asc(), RegionalPartnerModel.theme.asc()).all()
        return [RegionalPartnerResponse.model_validate(r) for r in rows]

    def create_partner(self, db: Session, partner_in: RegionalPartnerCreate) -> RegionalPartnerResponse:
        self.ensure_seeded(db)
        row = RegionalPartnerModel(**partner_in.model_dump())
        db.add(row)
        db.commit()
        db.refresh(row)
        return RegionalPartnerResponse.model_validate(row)

    def update_partner(self, db: Session, partner_id: int, partner_in: RegionalPartnerUpdate) -> Optional[RegionalPartnerResponse]:
        self.ensure_seeded(db)
        row = db.query(RegionalPartnerModel).filter(RegionalPartnerModel.id == partner_id).first()
        if not row:
            return None
        for k, v in partner_in.model_dump(exclude_unset=True).items():
            setattr(row, k, v)
        db.commit()
        db.refresh(row)
        return RegionalPartnerResponse.model_validate(row)

    def delete_partner(self, db: Session, partner_id: int) -> bool:
        self.ensure_seeded(db)
        row = db.query(RegionalPartnerModel).filter(RegionalPartnerModel.id == partner_id).first()
        if not row:
            return False
        db.delete(row)
        db.commit()
        return True

    def resolve_partner_for_initiative(
        self,
        db: Optional[Session],
        location: str,
        theme: str,
        toms_code: Optional[str]
    ) -> str:
        """Dynamically finds the best approved regional partner for this location and theme."""
        if db:
            try:
                self.ensure_seeded(db)
                loc_clean = (location or "birmingham").lower().strip()
                # 1. Try matching location + toms_code
                if toms_code:
                    match = db.query(RegionalPartnerModel).filter(
                        RegionalPartnerModel.location.ilike(f"%{loc_clean}%"),
                        RegionalPartnerModel.toms_code.ilike(f"%{toms_code.strip()}%"),
                        RegionalPartnerModel.is_approved.is_(True)
                    ).first()
                    if match:
                        return match.partner_name

                # 2. Try matching location + theme
                match = db.query(RegionalPartnerModel).filter(
                    RegionalPartnerModel.location.ilike(f"%{loc_clean}%"),
                    RegionalPartnerModel.theme.ilike(f"%{theme.strip()}%"),
                    RegionalPartnerModel.is_approved.is_(True)
                ).first()
                if match:
                    return match.partner_name

                # 3. Try matching National UK
                match = db.query(RegionalPartnerModel).filter(
                    RegionalPartnerModel.location.ilike("%national%"),
                    RegionalPartnerModel.theme.ilike(f"%{theme.strip()}%"),
                    RegionalPartnerModel.is_approved.is_(True)
                ).first()
                if match:
                    return match.partner_name
            except Exception:
                pass

        # In-memory default fallback
        loc_lower = (location or "birmingham").lower()
        for item in DEFAULT_PARTNERS_DATA:
            if item["location"].lower() in loc_lower or loc_lower in item["location"].lower():
                if toms_code and item.get("toms_code") == toms_code:
                    return item["partner_name"]
                if item["theme"].lower() in theme.lower():
                    return item["partner_name"]

        return "Approved Regional Partner Ecosystem"


partner_service = PartnerService()
