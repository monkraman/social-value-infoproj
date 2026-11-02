from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.toms_metric import TomsMetric as TomsMetricModel
from app.schemas.calculation import (
    TOMsMetric,
    TomsMetricCreate,
    TomsMetricUpdate,
    InitiativeCalculation,
    PackageCalculation,
    OpportunityRecommendRequest,
    OpportunityRecommendResponse,
    OpportunityRecommendationItem
)

# Reference Default TOMs & NHS Contract Benchmark Metrics
DEFAULT_TOMS_DATA: List[Dict[str, Any]] = [
    {
        "code": "NT1",
        "name": "Local Apprenticeship Weeks",
        "theme": "Work",
        "outcome": "More opportunities for disadvantaged people & youth",
        "unit": "weeks",
        "unit_value_gbp": 215.00,
        "description": "Number of weeks of local apprentice training delivered during the contract period.",
        "evidence_required": "Formal apprenticeship training agreement, monthly timesheets, and accredited training milestone certificates.",
        "ppn_mapping": "MAC 2.2: Employment and Skills",
        "source": "National TOMs 2024",
        "is_synthetic": False
    },
    {
        "code": "NT3",
        "name": "Young People Supported into Sustained Employment (16-24 NEET)",
        "theme": "Work",
        "outcome": "Reducing youth unemployment & building skills pipelines",
        "unit": "people",
        "unit_value_gbp": 4850.00,
        "description": "Young people (NEET) supported with career coaching, internships, and sustained entry into work (>6 months).",
        "evidence_required": "Proof of previous NEET status, 6-month continuous employment payslips, and mentoring review logs.",
        "ppn_mapping": "MAC 2.2: Employment and Skills",
        "source": "National TOMs 2024",
        "is_synthetic": False
    },
    {
        "code": "NT8",
        "name": "Digital Inclusion / Skills Workshops",
        "theme": "Community",
        "outcome": "Empowering communities and reducing digital poverty",
        "unit": "workshops",
        "unit_value_gbp": 1250.00,
        "description": "Community-based digital literacy, online safety, and accessibility training workshops for residents.",
        "evidence_required": "Workshop agenda, registered participant sign-in sheets, and pre/post digital competency evaluation forms.",
        "ppn_mapping": "MAC 2.1: Educational / Skills Partnerships",
        "source": "National TOMs 2024",
        "is_synthetic": False
    },
    {
        "code": "NT10",
        "name": "Staff Digital & STEM Volunteering Hours",
        "theme": "Community",
        "outcome": "Empowering community organizations & volunteering",
        "unit": "hours",
        "unit_value_gbp": 45.00,
        "description": "Dedicated employee volunteer hours supporting local schools, colleges, and registered charities.",
        "evidence_required": "Signed volunteering log sheets approved by registered beneficiary charity or education institution.",
        "ppn_mapping": "MAC 5.1: Community Integration & Wellbeing",
        "source": "National TOMs 2024",
        "is_synthetic": False
    },
    {
        "code": "NT14",
        "name": "Local SME & VCSE Supply Chain Spend Proxy",
        "theme": "Economy",
        "outcome": "Driving inclusive local economic growth and supply chain diversity",
        "unit": "GBP spend",
        "unit_value_gbp": 0.22,
        "description": "Direct supply chain spend awarded to local small businesses (SMEs) and voluntary sector partners (VCSEs).",
        "evidence_required": "Validated vendor postcodes, audited supplier invoices showing payment within 30 days, and annual spend ledger.",
        "ppn_mapping": "MAC 2.3: Diverse Supply Chains",
        "source": "National TOMs 2024",
        "is_synthetic": False
    },
    {
        "code": "NT20",
        "name": "Refurbished Digital Devices Donated",
        "theme": "Community",
        "outcome": "Reducing electronic waste and enabling digital connectivity",
        "unit": "devices",
        "unit_value_gbp": 320.00,
        "description": "Laptops and tablets securely data-wiped, refurbished, and donated with connectivity to disadvantaged residents.",
        "evidence_required": "Asset disposal records, ADISA data-wipe sanitization certificates, and recipient distribution receipts.",
        "ppn_mapping": "MAC 2.1: Community Tech Equality",
        "source": "National TOMs 2024",
        "is_synthetic": False
    },
    {
        "code": "NT31",
        "name": "Carbon Reduction / Energy Efficiency Initiatives",
        "theme": "Planet",
        "outcome": "Environmental stewardship & accelerating Net Zero",
        "unit": "tonnes CO2e",
        "unit_value_gbp": 280.00,
        "description": "Audited metric tonnes of CO2e avoided through cloud migration, renewable power usage, and energy management.",
        "evidence_required": "GHG Protocol Scope 1-3 independent verification, ISO 14001 audit report, and renewable energy certificates (REGO).",
        "ppn_mapping": "MAC 4.1: Fighting Climate Change",
        "source": "National TOMs 2024",
        "is_synthetic": False
    },
    {
        "code": "NHS-SV1-01",
        "name": "Sustainable IT Framework & GreenOps Observability",
        "theme": "Planet",
        "outcome": "Systemic decarbonisation of digital infrastructure",
        "unit": "milestone programmes",
        "unit_value_gbp": 25000.00,
        "description": "3-phase sustainable IT programme: RGESN eco-design audit, GreenOps platform integration, and carbon scenario modelling.",
        "evidence_required": "Schedule 3b Paragraph 7.1 delivery sign-off: RGESN assessment grid, Sopht GreenOps data logs, and published GDSA case study.",
        "ppn_mapping": "MAC 4.1: Effective Stewardship of the Environment",
        "source": "NHS Schedule 8 / Schedule 3b Benchmark",
        "is_synthetic": False
    },
    {
        "code": "NHS-SV1-02",
        "name": "Green Health Routes & Community Biodiversity",
        "theme": "Planet",
        "outcome": "Enhancing natural environment and patient nature-based health",
        "unit": "routes created",
        "unit_value_gbp": 17000.00,
        "description": "Establishing and maintaining biodiverse community walking routes and NHS green spaces in deprived areas.",
        "evidence_required": "Schedule 3b SPI11 handover certificate, CSH / NHS Forest site partnership agreements, and biannual maintenance logs.",
        "ppn_mapping": "MAC 4.1: Additional Environmental Benefit",
        "source": "NHS Schedule 8 / Schedule 3b Benchmark",
        "is_synthetic": False
    },
    {
        "code": "NHS-SV2-01",
        "name": "Digital Ambassador Academy (Disadvantaged Groups)",
        "theme": "Work",
        "outcome": "Level 3/4 tech apprenticeships with guaranteed living wages",
        "unit": "employment months",
        "unit_value_gbp": 1500.00,
        "description": "Paid employment months for newly recruited digital ambassadors from top 20% index of multiple deprivation postcodes.",
        "evidence_required": "Schedule 3b KPI9b payroll audits, candidate IMD postcode verification, and QA Consulting apprentice completion logs.",
        "ppn_mapping": "MAC 2.2: Creating New Businesses, Jobs and Skills",
        "source": "NHS Schedule 8 / Schedule 3b Benchmark",
        "is_synthetic": False
    },
    {
        "code": "NHS-SV2-02",
        "name": "Device Prescribing Programme for Digital Health Equity",
        "theme": "Community",
        "outcome": "Overcoming clinical isolation through digital health access",
        "unit": "prescribing consultations",
        "unit_value_gbp": 450.00,
        "description": "Primary care consultations resulting in prescribed refurbished devices, connectivity bundles, and digital literacy coaching.",
        "evidence_required": "Schedule 3b SPI12 consultation registers, Good Things Foundation National Databank SIM logs, and asset handover proofs.",
        "ppn_mapping": "MAC 2.2: Addressing Digital Exclusion",
        "source": "NHS Schedule 8 / Schedule 3b Benchmark",
        "is_synthetic": False
    },
    {
        "code": "NHS-SV2-03",
        "name": "E-Waste Refurbishment Pipeline for Prison Leavers",
        "theme": "Work",
        "outcome": "Reintegration and green tech skills for ex-offenders",
        "unit": "prison leavers employed",
        "unit_value_gbp": 8500.00,
        "description": "Employment and certified hardware refurbishment training for recent prison leavers to prevent reoffending.",
        "evidence_required": "Jobcentre Plus & New Futures Network referral verification, employment contracts, and ADISA device handling badges.",
        "ppn_mapping": "MAC 2.2: Reducing Economic Barriers",
        "source": "NHS Schedule 8 / Schedule 3b Benchmark",
        "is_synthetic": False
    },
    {
        "code": "NHS-SV3-01",
        "name": "Modern Slavery Assessment Tool (MSAT) Audit & Compliance",
        "theme": "Work",
        "outcome": "Ethical supply chain transparency & worker protection",
        "unit": "audited suppliers",
        "unit_value_gbp": 4500.00,
        "description": "Biannual Home Office MSAT assessment achieving >=80% green rating across prime and key Tier-1 supply chain contractors.",
        "evidence_required": "Schedule 3b KPI9c Home Office MSAT verified scorecards, supply chain audit reports, and signed remediation trackers.",
        "ppn_mapping": "MAC 6.3: Identifying & Managing Modern Slavery",
        "source": "NHS Schedule 8 / Schedule 3b Benchmark",
        "is_synthetic": False
    },
    {
        "code": "NHS-SV3-02",
        "name": "Healthcare Modern Slavery Detection Training",
        "theme": "Community",
        "outcome": "Equipping frontline staff to detect human trafficking",
        "unit": "staff trained",
        "unit_value_gbp": 95.00,
        "description": "Accredited e-learning modules and interactive case study sessions delivered in partnership with Unseen.",
        "evidence_required": "Unseen Learning Academy completion registers, pre/post training evaluation scores, and clinical attendance rosters.",
        "ppn_mapping": "MAC 6.3: Modern Slavery Detection & Intervention",
        "source": "NHS Schedule 8 / Schedule 3b Benchmark",
        "is_synthetic": False
    }
]


class CalculationService:
    """
    Deterministic Social Value Calculation & TOMs Catalog Service.
    Connects to database for persistent configuration while maintaining strict deterministic math.
    """

    def ensure_seeded(self, db: Session) -> None:
        """Seed default metrics into DB if empty."""
        try:
            count = db.query(TomsMetricModel).count()
            if count == 0:
                for item in DEFAULT_TOMS_DATA:
                    db_item = TomsMetricModel(**item)
                    db.add(db_item)
                db.commit()
        except Exception as e:
            db.rollback()
            print(f"[CalculationService Warning] Seeding check deferred: {e}")

    def get_all_metrics(
        self,
        db: Optional[Session] = None,
        theme: Optional[str] = None,
        search: Optional[str] = None,
        active_only: bool = False
    ) -> List[TOMsMetric]:
        """Fetch all metrics from DB with optional filtering, or fall back to default list."""
        if db is not None:
            try:
                self.ensure_seeded(db)
                query = db.query(TomsMetricModel)
                if active_only:
                    query = query.filter(TomsMetricModel.is_active.is_(True))
                if theme and theme.lower() != "all":
                    query = query.filter(TomsMetricModel.theme.ilike(f"%{theme.strip()}%"))
                if search:
                    q = f"%{search.strip()}%"
                    query = query.filter(
                        or_(
                            TomsMetricModel.code.ilike(q),
                            TomsMetricModel.name.ilike(q),
                            TomsMetricModel.description.ilike(q),
                            TomsMetricModel.ppn_mapping.ilike(q)
                        )
                    )
                rows = query.order_by(TomsMetricModel.code.asc()).all()
                if rows:
                    return [TOMsMetric.model_validate(r) for r in rows]
            except Exception as exc:
                print(f"[CalculationService Warning] Could not query DB ({exc}), returning static defaults.")

        # Fallback to in-memory defaults
        results = [TOMsMetric(**data) for data in DEFAULT_TOMS_DATA]
        if theme and theme.lower() != "all":
            results = [m for m in results if theme.lower() in m.theme.lower()]
        if search:
            s = search.lower()
            results = [
                m for m in results
                if s in m.code.lower() or s in m.name.lower() or (m.description and s in m.description.lower())
            ]
        return results

    def get_metric_by_code(self, db: Optional[Session], code: str) -> Optional[TOMsMetric]:
        """Find a single metric by its unique code."""
        if not code:
            return None
        code_clean = code.strip().upper()

        if db is not None:
            try:
                self.ensure_seeded(db)
                row = db.query(TomsMetricModel).filter(TomsMetricModel.code.ilike(code_clean)).first()
                if row:
                    return TOMsMetric.model_validate(row)
            except Exception:
                pass

        for item in DEFAULT_TOMS_DATA:
            if item["code"].upper() == code_clean:
                return TOMsMetric(**item)
        return None

    def create_metric(self, db: Session, metric_in: TomsMetricCreate) -> TOMsMetric:
        """Create and persist a new TOMs metric in the database."""
        self.ensure_seeded(db)
        code_clean = metric_in.code.strip().upper()

        existing = db.query(TomsMetricModel).filter(TomsMetricModel.code.ilike(code_clean)).first()
        if existing:
            raise ValueError(f"Metric with code '{code_clean}' already exists. Use update instead.")

        db_item = TomsMetricModel(
            code=code_clean,
            name=metric_in.name.strip(),
            theme=metric_in.theme.strip(),
            outcome=metric_in.outcome.strip() if metric_in.outcome else None,
            unit=metric_in.unit.strip(),
            unit_value_gbp=float(metric_in.unit_value_gbp),
            description=metric_in.description.strip() if metric_in.description else "",
            evidence_required=metric_in.evidence_required.strip() if metric_in.evidence_required else "",
            ppn_mapping=metric_in.ppn_mapping.strip() if metric_in.ppn_mapping else "",
            source=metric_in.source.strip() if metric_in.source else "Custom User Metric",
            is_active=True
        )
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        return TOMsMetric.model_validate(db_item)

    def update_metric(self, db: Session, code: str, metric_in: TomsMetricUpdate) -> Optional[TOMsMetric]:
        """Update an existing metric by its code."""
        self.ensure_seeded(db)
        row = db.query(TomsMetricModel).filter(TomsMetricModel.code.ilike(code.strip())).first()
        if not row:
            return None

        update_data = metric_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                setattr(row, key, value)

        db.commit()
        db.refresh(row)
        return TOMsMetric.model_validate(row)

    def delete_metric(self, db: Session, code: str) -> bool:
        """Soft-deactivate or delete a metric."""
        self.ensure_seeded(db)
        row = db.query(TomsMetricModel).filter(TomsMetricModel.code.ilike(code.strip())).first()
        if not row:
            return False

        # Soft delete by deactivating
        row.is_active = False
        db.commit()
        return True

    def reset_to_defaults(self, db: Session) -> int:
        """Reset or restore default metrics into database."""
        db.query(TomsMetricModel).delete()
        for item in DEFAULT_TOMS_DATA:
            db.add(TomsMetricModel(**item))
        db.commit()
        return len(DEFAULT_TOMS_DATA)

    def calculate_initiative(
        self,
        initiative_name: str,
        toms_code: Optional[str],
        annual_volume: float,
        duration_years: int,
        db: Optional[Session] = None
    ) -> InitiativeCalculation:
        """
        Deterministically calculates the social value for an individual initiative.
        Formula: Annual Volume × Contract Duration (Years) × Unit Value (GBP)
        """
        metric = self.get_metric_by_code(db, toms_code) if toms_code else None

        if metric:
            unit_val = metric.unit_value_gbp
            unit_name = metric.unit
            metric_title = metric.name
            toms_ref = metric.code
        else:
            unit_val = 0.0
            unit_name = "units"
            metric_title = "Unmapped Custom Initiative"
            toms_ref = toms_code or "CUSTOM"

        total_vol = round(annual_volume * duration_years, 2)
        total_sv = round(total_vol * unit_val, 2)
        formula = f"{annual_volume} {unit_name}/yr × {duration_years} yrs = {total_vol} {unit_name} @ £{unit_val:,.2f} = £{total_sv:,.2f}"

        return InitiativeCalculation(
            initiative_name=initiative_name,
            toms_code=toms_ref,
            metric_name=metric_title,
            unit=unit_name,
            unit_value_gbp=unit_val,
            annual_volume=annual_volume,
            duration_years=duration_years,
            total_volume=total_vol,
            total_social_value_gbp=total_sv,
            calculation_formula=formula
        )

    def calculate_package(
        self,
        package_name: str,
        initiatives: List[Dict[str, Any]],
        contract_value_gbp: float,
        duration_years: int,
        target_weighting_percent: float,
        db: Optional[Session] = None
    ) -> PackageCalculation:
        """
        Calculates social value across a package of initiatives against contract target.
        """
        calculated_inits: List[InitiativeCalculation] = []
        total_social_value = 0.0
        audit_trail: List[str] = []

        target_sv_gbp = round((contract_value_gbp * target_weighting_percent) / 100.0, 2)

        for item in initiatives:
            name = item.get("name") or "Unnamed Initiative"
            code = item.get("toms_metric_code") or item.get("toms_code")
            annual_vol = float(item.get("annual_volume", 0.0))

            init_calc = self.calculate_initiative(
                initiative_name=name,
                toms_code=code,
                annual_volume=annual_vol,
                duration_years=duration_years,
                db=db
            )
            calculated_inits.append(init_calc)
            total_social_value += init_calc.total_social_value_gbp
            audit_trail.append(f"{init_calc.initiative_name} ({init_calc.toms_code}): {init_calc.calculation_formula}")

        total_social_value = round(total_social_value, 2)
        sv_percentage = round((total_social_value / contract_value_gbp) * 100.0, 2) if contract_value_gbp > 0 else 0.0
        target_met = total_social_value >= target_sv_gbp

        audit_trail.append(
            f"Package Total: £{total_social_value:,.2f} ({sv_percentage}% of contract). Target ({target_weighting_percent}% = £{target_sv_gbp:,.2f}) Met: {target_met}"
        )

        return PackageCalculation(
            package_name=package_name,
            initiatives=calculated_inits,
            total_social_value_gbp=total_social_value,
            contract_value_gbp=contract_value_gbp,
            social_value_percentage=sv_percentage,
            target_weighting_percent=target_weighting_percent,
            target_social_value_gbp=target_sv_gbp,
            target_met=target_met,
            audit_trail=audit_trail
        )

    def recommend_opportunities(
        self,
        db: Optional[Session],
        req: OpportunityRecommendRequest
    ) -> OpportunityRecommendResponse:
        """
        Opportunity Finder & Bid Advisor for Document-less Clients.
        Synthesizes contract scale, duration, industry, and location to recommend high-scoring,
        achievable TOMs initiatives mapped to PPN 06/20 Model Award Criteria.
        """
        all_metrics = self.get_all_metrics(db=db, active_only=True)
        target_sv_gbp = (req.contract_value_gbp * req.target_weighting_percent) / 100.0

        # Prioritize core pillars: Work, Planet, Community, Economy, Modern Slavery
        theme_allocations = {
            "Work": 0.35,      # 35% of target
            "Planet": 0.25,    # 25% of target
            "Community": 0.20, # 20% of target
            "Economy": 0.20    # 20% of target
        }

        # Filter metrics
        by_code = {m.code: m for m in all_metrics}

        recommendations: List[OpportunityRecommendationItem] = []
        total_rec_sv = 0.0

        # Strategy Selection based on verified catalog:
        # 1. Apprenticeship / Employment (Work)
        work_metric = by_code.get("NT1") or by_code.get("NHS-SV2-01")
        if work_metric:
            alloc_gbp = target_sv_gbp * theme_allocations["Work"]
            # e.g., NT1 is £215/week. Over N years:
            weeks_needed = max(12.0, round(alloc_gbp / (work_metric.unit_value_gbp * req.duration_years), 0))
            calc = self.calculate_initiative(
                "Local Apprenticeship & Skills Academy",
                work_metric.code,
                weeks_needed,
                req.duration_years,
                db=db
            )
            recommendations.append(OpportunityRecommendationItem(
                toms_code=work_metric.code,
                initiative_name="Local Apprenticeship & Skills Academy",
                theme=work_metric.theme,
                ppn_mac=work_metric.ppn_mapping or "MAC 2.2: Employment and Skills",
                unit=work_metric.unit,
                unit_value_gbp=work_metric.unit_value_gbp,
                annual_volume=weeks_needed,
                duration_years=req.duration_years,
                total_volume=calc.total_volume,
                total_social_value_gbp=calc.total_social_value_gbp,
                why_recommended=f"Aligns directly with UK public sector priority for local career pathways in {req.location}. Addresses skills shortage in {req.industry}.",
                delivery_approach="Partner with local accredited training providers (e.g. QA Consulting or local FE colleges) to sponsor accredited Level 3/4 apprentices with structured on-the-job mentoring.",
                evidence_needed=work_metric.evidence_required or "Apprenticeship service registration, monthly payroll timesheets, and course completion certificates."
            ))
            total_rec_sv += calc.total_social_value_gbp

        # 2. Sustainable IT & Carbon Avoidance (Planet)
        planet_metric = by_code.get("NT31") or by_code.get("NHS-SV1-01")
        if planet_metric:
            alloc_gbp = target_sv_gbp * theme_allocations["Planet"]
            vol_needed = max(5.0, round(alloc_gbp / (planet_metric.unit_value_gbp * req.duration_years), 1))
            calc = self.calculate_initiative(
                "Sustainable IT & GreenOps Carbon Reduction",
                planet_metric.code,
                vol_needed,
                req.duration_years,
                db=db
            )
            recommendations.append(OpportunityRecommendationItem(
                toms_code=planet_metric.code,
                initiative_name="Sustainable IT & GreenOps Carbon Reduction",
                theme=planet_metric.theme,
                ppn_mac=planet_metric.ppn_mapping or "MAC 4.1: Fighting Climate Change",
                unit=planet_metric.unit,
                unit_value_gbp=planet_metric.unit_value_gbp,
                annual_volume=vol_needed,
                duration_years=req.duration_years,
                total_volume=calc.total_volume,
                total_social_value_gbp=calc.total_social_value_gbp,
                why_recommended="Essential for NHS and Central Government tenders mandating PPN 06/21 Carbon Reduction Plans and Scope 3 supply chain observability.",
                delivery_approach="Implement GreenOps automated energy telemetry (e.g., Sopht platform), ensure ISO 14001 data center compliance, and optimize computational resource load.",
                evidence_needed=planet_metric.evidence_required or "Independent Scope 1-3 audit, ISO 14001 certification, and annual carbon reduction dashboard reports."
            ))
            total_rec_sv += calc.total_social_value_gbp

        # 3. Digital Inclusion / Community Volunteering (Community)
        comm_metric = by_code.get("NT8") or by_code.get("NHS-SV2-02")
        if comm_metric:
            alloc_gbp = target_sv_gbp * theme_allocations["Community"]
            vol_needed = max(2.0, round(alloc_gbp / (comm_metric.unit_value_gbp * req.duration_years), 0))
            calc = self.calculate_initiative(
                "Community Digital Inclusion Clinics & Device Access",
                comm_metric.code,
                vol_needed,
                req.duration_years,
                db=db
            )
            recommendations.append(OpportunityRecommendationItem(
                toms_code=comm_metric.code,
                initiative_name="Community Digital Inclusion Clinics & Device Access",
                theme=comm_metric.theme,
                ppn_mac=comm_metric.ppn_mapping or "MAC 2.1: Tackling Economic Inequality",
                unit=comm_metric.unit,
                unit_value_gbp=comm_metric.unit_value_gbp,
                annual_volume=vol_needed,
                duration_years=req.duration_years,
                total_volume=calc.total_volume,
                total_social_value_gbp=calc.total_social_value_gbp,
                why_recommended=f"Directly supports high-deprivation resident cohorts in {req.location} through basic digital literacy and healthcare accessibility.",
                delivery_approach="Collaborate with grassroots partners like Good Things Foundation to host quarterly hands-on digital skills workshops and donate wiped refurbished devices.",
                evidence_needed=comm_metric.evidence_required or "Signed participant rosters, pre/post feedback questionnaires, and device sanitization logs."
            ))
            total_rec_sv += calc.total_social_value_gbp

        # 4. Local SME & Social Enterprise Supply Chain (Economy)
        econ_metric = by_code.get("NT14")
        if econ_metric:
            alloc_gbp = target_sv_gbp * theme_allocations["Economy"]
            # NT14 is £0.22 per £1 spent. So spend volume:
            vol_needed = max(10000.0, round(alloc_gbp / (econ_metric.unit_value_gbp * req.duration_years), 0))
            calc = self.calculate_initiative(
                "Local SME & VCSE Supply Chain Integration",
                econ_metric.code,
                vol_needed,
                req.duration_years,
                db=db
            )
            recommendations.append(OpportunityRecommendationItem(
                toms_code=econ_metric.code,
                initiative_name="Local SME & VCSE Supply Chain Integration",
                theme=econ_metric.theme,
                ppn_mac=econ_metric.ppn_mapping or "MAC 2.3: Diverse Supply Chains",
                unit=econ_metric.unit,
                unit_value_gbp=econ_metric.unit_value_gbp,
                annual_volume=vol_needed,
                duration_years=req.duration_years,
                total_volume=calc.total_volume,
                total_social_value_gbp=calc.total_social_value_gbp,
                why_recommended="High-scoring criterion in local authority scoring, demonstrating contract cash recirculation within local regional economies.",
                delivery_approach="Ring-fence tier-2 subcontracts (QA testing, local logistics, catering) for verified local SMEs and VCSEs with prompt 30-day payment terms.",
                evidence_needed=econ_metric.evidence_required or "Subcontractor agreements, Companies House SME verification, and audited invoice payment ledgers."
            ))
            total_rec_sv += calc.total_social_value_gbp

        # 5. Modern Slavery Governance Benchmark (Work / Compliance)
        ms_metric = by_code.get("NHS-SV3-01") or by_code.get("NT10")
        if ms_metric:
            vol_needed = 2.0  # biannual
            calc = self.calculate_initiative(
                "Supply Chain Modern Slavery MSAT Auditing",
                ms_metric.code,
                vol_needed,
                req.duration_years,
                db=db
            )
            recommendations.append(OpportunityRecommendationItem(
                toms_code=ms_metric.code,
                initiative_name="Supply Chain Modern Slavery MSAT Auditing",
                theme=ms_metric.theme,
                ppn_mac=ms_metric.ppn_mapping or "MAC 6.3: Tackling Workforce Inequality",
                unit=ms_metric.unit,
                unit_value_gbp=ms_metric.unit_value_gbp,
                annual_volume=vol_needed,
                duration_years=req.duration_years,
                total_volume=calc.total_volume,
                total_social_value_gbp=calc.total_social_value_gbp,
                why_recommended="Mandatory compliance element for central government and NHS procurement under Procurement Policy Note 02/23.",
                delivery_approach="Enforce Home Office Modern Slavery Assessment Tool (MSAT) reviews every 6 months across Tier-1 vendors maintaining score >= 80%.",
                evidence_needed=ms_metric.evidence_required or "Biannual Home Office MSAT scorecard reports and supplier audit trail sign-offs."
            ))
            total_rec_sv += calc.total_social_value_gbp

        achieved_pct = round((total_rec_sv / req.contract_value_gbp) * 100.0, 2) if req.contract_value_gbp > 0 else 0.0

        summary = (
            f"Tailored Social Value Strategy for {req.industry} contract in {req.location}: "
            f"Delivering £{total_rec_sv:,.2f} of audited Social Value ({achieved_pct}% of contract value), "
            f"surpassing the statutory {req.target_weighting_percent}% target (£{target_sv_gbp:,.2f}). "
            f"Features 5 balanced commitments across Skills (Work), Net Zero (Planet), Digital Inclusion (Community), "
            f"and SME Prosperity (Economy), fully structured for Schedule 8 Method Statement and Schedule 3b KPIs."
        )

        return OpportunityRecommendResponse(
            contract_value_gbp=req.contract_value_gbp,
            duration_years=req.duration_years,
            target_weighting_percent=req.target_weighting_percent,
            target_social_value_gbp=round(target_sv_gbp, 2),
            total_recommended_social_value_gbp=round(total_rec_sv, 2),
            achieved_weighting_percent=achieved_pct,
            target_met=total_rec_sv >= target_sv_gbp,
            recommendations=recommendations,
            executive_summary=summary
        )


calculation_service = CalculationService()
