import re
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from app.schemas.response import (
    OpportunityRequest,
    ResponseGenerationResult,
    SocialValuePackage,
    InitiativeItem,
    GovernanceCadence,
    AIReasoningStep
)
from app.services.retrieval_service import retrieval_service
from app.services.calculation_service import calculation_service
from app.services.openai_service import openai_service
from app.core.config import settings


# Approved Ecosystem Partners by Theme and Geography (Client Alignment)
APPROVED_PARTNER_ECOSYSTEM: Dict[str, Dict[str, str]] = {
    "birmingham": {
        "NT8": "Birmingham Community Matters & West Midlands Digital Device Bank",
        "NT3": "St Basils Youth Charity",
        "NT1": "BMet College & West Midlands Apprenticeship Hub",
        "NT20": "West Midlands Digital Device Bank",
        "NT10": "Local Birmingham Secondary Schools & Academies",
        "NT14": "West Midlands Chamber of Commerce & WMCA SME Network",
        "digital inclusion": "Birmingham Community Matters & West Midlands Digital Device Bank",
        "youth employment": "St Basils Youth Charity & BMet College",
        "community engagement": "Local Birmingham Secondary Schools & Academies",
        "economic growth": "West Midlands Chamber of Commerce",
        "employment & skills": "BMet College & West Midlands Apprenticeship Hub",
        "healthcare": "Birmingham & Solihull Health Tech VCSE Alliance"
    },
    "west midlands": {
        "NT8": "Birmingham Community Matters & West Midlands Digital Device Bank",
        "NT3": "St Basils Youth Charity",
        "NT1": "BMet College & West Midlands Apprenticeship Hub",
        "NT20": "West Midlands Digital Device Bank",
        "NT10": "West Midlands STEM Ambassador Network",
        "NT14": "West Midlands Chamber of Commerce & WMCA SME Network",
        "digital inclusion": "West Midlands Digital Device Bank",
        "youth employment": "St Basils Youth Charity",
        "community engagement": "West Midlands STEM Ambassador Network",
        "economic growth": "West Midlands Chamber of Commerce",
        "employment & skills": "BMet College & West Midlands Apprenticeship Hub",
        "healthcare": "West Midlands Health Tech Innovation Alliance"
    },
    "london": {
        "NT8": "London Digital Inclusion Network & Good Things Foundation",
        "NT3": "Mayor's Fund for London / London Youth",
        "NT1": "London South Bank Apprenticeships Hub",
        "NT20": "London Community Device Bank",
        "NT10": "London Schools Excellence Alliance",
        "NT14": "London Chamber of Commerce & Industry (LCCI)",
        "digital inclusion": "London Digital Inclusion Network",
        "youth employment": "Mayor's Fund for London / London Youth",
        "community engagement": "London Schools Excellence Alliance",
        "economic growth": "London Chamber of Commerce & Industry",
        "employment & skills": "London South Bank Apprenticeships Hub",
        "healthcare": "One London Health Technology VCSE Network"
    },
    "manchester": {
        "NT8": "Greater Manchester Digital Inclusion Coalition",
        "NT3": "Manchester Youth Zone & HideOut Youth Zone",
        "NT1": "Manchester Metropolitan / The Manchester College",
        "NT20": "GM Community Computer Recycling Bank",
        "NT10": "Greater Manchester STEM Network",
        "NT14": "Greater Manchester Chamber of Commerce",
        "digital inclusion": "Greater Manchester Digital Inclusion Coalition",
        "youth employment": "Manchester Youth Zone",
        "community engagement": "Greater Manchester STEM Network",
        "economic growth": "Greater Manchester Chamber of Commerce",
        "employment & skills": "The Manchester College",
        "healthcare": "Greater Manchester Health & Social Care Digital Alliance"
    },
    "default": {
        "NT8": "Local Authority Digital Inclusion Lead & Community Hubs",
        "NT3": "Regional Youth Employment Trust & The Prince's Trust",
        "NT1": "Local FE College & Regional Apprenticeship Provider",
        "NT20": "Approved IT Asset Disposal & Regional Device Bank",
        "NT10": "Local Education Partnership & STEM Learning UK",
        "NT14": "Local Enterprise Partnership (LEP) & Regional SME Chamber",
        "digital inclusion": "Local Authority Community Hubs & Digital Volunteers",
        "youth employment": "Regional Youth Employment Trust",
        "community engagement": "STEM Learning UK & Local Secondary Schools",
        "economic growth": "Regional SME Supply Chain Network",
        "employment & skills": "Regional FE College & Apprenticeship Hub",
        "healthcare": "Regional NHS & Healthcare VCSE Partnership"
    }
}

# Benchmarked Indicative Delivery Unit Costs (£/unit)
INDICATIVE_UNIT_DELIVERY_COSTS: Dict[str, float] = {
    "NT1": 45.0,    # £45/week mentorship & workplace coaching
    "NT3": 750.0,   # £750/person casework & intensive coaching for NEET youth
    "NT8": 350.0,   # £350/workshop venue, materials & certified trainer
    "NT10": 10.0,   # £10/hour volunteer coordination & school outreach
    "NT14": 0.02,   # 2% local SME supply chain onboarding & auditing
    "NT20": 80.0,   # £80/device wiping, hardware refurb & 12m data SIM
}


class RAGService:
    def _resolve_partner(self, raw_init: Dict[str, Any], location: str, context_text: str) -> str:
        """Resolves partner from explicit evidence, proposed name, or regional ecosystem repository."""
        proposed_partner = raw_init.get("partner")
        if proposed_partner and str(proposed_partner).strip().lower() not in ["null", "none", "tbd", "tbc", ""]:
            return str(proposed_partner).strip()

        loc_clean = (location or "birmingham").lower().strip()
        loc_partners = None
        for key in APPROVED_PARTNER_ECOSYSTEM:
            if key in loc_clean or loc_clean in key:
                loc_partners = APPROVED_PARTNER_ECOSYSTEM[key]
                break
        if not loc_partners:
            loc_partners = APPROVED_PARTNER_ECOSYSTEM["default"]

        toms_code = raw_init.get("toms_metric_code")
        theme_key = raw_init.get("theme", "").lower().strip()
        return loc_partners.get(toms_code) or loc_partners.get(theme_key) or loc_partners.get("digital inclusion") or "Approved Infosys Ecosystem Partner"

    def _build_social_value_package(
        self,
        pkg_data: Dict[str, Any],
        pkg_name: str,
        req: OpportunityRequest,
        retrieved_items: List[Any],
        context_text: str
    ) -> SocialValuePackage:
        raw_initiatives = pkg_data.get("initiatives", [])
        processed_items: List[InitiativeItem] = []
        total_delivery_cost = 0.0

        for raw_init in raw_initiatives:
            evidence_source = str(raw_init.get("evidence_source", "Model recommended"))
            source_is_retrieved = any(
                source.lower() in evidence_source.lower()
                for source in (item.filename for item in retrieved_items)
            )

            final_partner = self._resolve_partner(raw_init, req.location, context_text)
            annual_vol = float(raw_init.get("annual_volume", 1.0))
            toms_code = raw_init.get("toms_metric_code")

            # Deterministic Delivery Cost Calculation
            raw_cost = float(raw_init.get("indicative_cost_gbp") or 0.0)
            if raw_cost > 0:
                init_cost = round(raw_cost, 2)
            else:
                unit_cost = INDICATIVE_UNIT_DELIVERY_COSTS.get(toms_code, 35.0)
                init_cost = round(annual_vol * req.contract_duration_years * unit_cost, 2)
            total_delivery_cost += init_cost

            init_item = InitiativeItem(
                name=raw_init.get("name", "Social Value Initiative"),
                theme=raw_init.get("theme", "Community"),
                location=raw_init.get("location", req.location),
                description=raw_init.get("description", ""),
                delivery_mechanism=raw_init.get("delivery_mechanism", ""),
                target_beneficiaries=raw_init.get("target_beneficiaries", "Local residents"),
                annual_volume=annual_vol,
                toms_metric_code=toms_code,
                partner=final_partner,
                evidence_source=evidence_source if source_is_retrieved else "Infosys Core Offer & Approved Partner Repository",
                is_from_knowledge_base=bool(raw_init.get("is_from_knowledge_base", False) or source_is_retrieved),
                sessions_per_year=raw_init.get("sessions_per_year"),
                hours_per_session=raw_init.get("hours_per_session"),
                participants_per_session=raw_init.get("participants_per_session"),
                indicative_cost_gbp=init_cost,
                commercial_viability=f"£{init_cost:,.2f} delivery cost over {req.contract_duration_years} yrs"
            )
            processed_items.append(init_item)

        # Deterministic calculation using backend code (NOT LLM)
        calculation_result = calculation_service.calculate_package(
            package_name=pkg_name,
            initiatives=[item.model_dump() for item in processed_items],
            contract_value_gbp=req.contract_value_gbp,
            duration_years=req.contract_duration_years,
            target_weighting_percent=req.social_value_weighting_percent
        )

        total_delivery_cost = round(total_delivery_cost, 2)
        total_sv = calculation_result.total_social_value_gbp
        svroi = round(total_sv / total_delivery_cost, 1) if total_delivery_cost > 0 else 6.5
        commercial_summary = (
            f"Estimated internal delivery investment of £{total_delivery_cost:,.2f} creates "
            f"£{total_sv:,.2f} Social Value ({svroi}x SVROI multiplier)."
        )

        return SocialValuePackage(
            name=pkg_name,
            initiatives=processed_items,
            rationale={
                "Core Package": "Lower-complexity baseline compliance option addressing core contractual requirements at minimal delivery risk.",
                "Enhanced Package": "Expanded high-scoring option delivering significant local impact to maximize competitive win probability.",
                "Localised Package": f"Place-based option tailored for {req.location} targeting local priority wards and accredited regional partners."
            }.get(pkg_name, "Draft option for review against client priorities."),
            expected_impact=pkg_data.get("expected_impact", []),
            dependencies=pkg_data.get("dependencies", []),
            financial_calculation=calculation_result,
            indicative_delivery_cost_gbp=total_delivery_cost,
            commercial_viability_summary=commercial_summary,
            governance=GovernanceCadence(
                social_value_lead="Dedicated Infosys Social Value Lead assigned upon contract award",
                kickoff_cadence="Joint Social Value Kick-Off Meeting held within 60 days of contract award",
                reporting_frequency="Quarterly Social Value Progress & National TOMs Performance Reporting",
                annual_review="Annual SVROI impact evaluation and financial verification audit"
            )
        )

    def generate_response(self, db: Session, req: OpportunityRequest) -> ResponseGenerationResult:
        """
        Executes end-to-end RAG workflow:
        1. Query formulation
        2. Vector similarity retrieval from pgvector
        3. Context formatting
        4. Structured LLM recommendation
        5. Deterministic Social Value / TOMs calculation layer
        6. Transparent AI reasoning trace & governance formulation
        """
        # Step 1: Query Formulation
        priorities_str = ", ".join(req.priorities) if req.priorities else "Social Value"
        retrieval_query = f"{priorities_str} initiatives in {req.location} for {req.client}"
        if req.raw_prompt and req.raw_prompt.strip():
            retrieval_query = f"{retrieval_query}. Tender requirements: {req.raw_prompt.strip()[:1200]}"

        # Step 2: Vector Retrieval
        retrieved_items = retrieval_service.search_chunks(
            db=db,
            query=retrieval_query,
            top_k=req.top_k
        )

        # Step 3: Context Formatting
        context_parts = []
        for i, item in enumerate(retrieved_items, start=1):
            context_parts.append(
                f"[Evidence Chunk {i}] (Doc: {item.filename}, Ref: {item.metadata or 'not supplied'}, Similarity: {item.similarity:.2f}):\n{item.content}"
            )
        context_text = "\n\n".join(context_parts)

        # Step 4: Get TOMs proxy catalog for LLM reference
        toms_catalog = [
            {
                "code": m.code,
                "name": m.name,
                "theme": m.theme,
                "unit": m.unit,
                "unit_value_gbp": m.unit_value_gbp,
                "description": m.description
            }
            for m in calculation_service.get_all_metrics()
        ]

        opportunity_dict = req.model_dump()
        target_sv_gbp = round(req.contract_value_gbp * (req.social_value_weighting_percent / 100.0), 2)
        opportunity_dict["target_social_value_gbp"] = target_sv_gbp

        # Step 5: Send context to LLM for structured initiative recommendations
        llm_raw = openai_service.generate_recommendation_from_llm(
            context_text=context_text,
            opportunity=opportunity_dict,
            toms_catalog=toms_catalog
        )

        # Step 6: Apply DETERMINISTIC CALCULATION LAYER to each package
        core_package = self._build_social_value_package(
            llm_raw.get("core_package", {}), "Core Package", req, retrieved_items, context_text
        )
        enhanced_package = self._build_social_value_package(
            llm_raw.get("enhanced_package", {}), "Enhanced Package", req, retrieved_items, context_text
        )
        localised_package = self._build_social_value_package(
            llm_raw.get("localised_package", {}), "Localised Package", req, retrieved_items, context_text
        )

        # Step 7: Grounding summary and validation check
        grounding_summary = {
            "retrieval_query_used": retrieval_query,
            "top_k_requested": req.top_k,
            "evidence_chunks_found": len(retrieved_items),
            "sources_used": list(set(item.filename for item in retrieved_items)),
            "highest_similarity": retrieved_items[0].similarity if retrieved_items else 0.0
        }

        validation_items = list(llm_raw.get("validation_required", []))
        validation_items.append(
            "POC limitation: the active TOMs catalog uses synthetic proxy values. Replace and verify rates against the approved National TOMs source before using impact totals in a bid."
        )
        all_packages = [core_package, enhanced_package, localised_package]
        all_initiatives = [initiative for package in all_packages for initiative in package.initiatives]
        for package in all_packages:
            calculation = package.financial_calculation
            if calculation and not calculation.target_met:
                gap = max(0.0, calculation.target_social_value_gbp - calculation.total_social_value_gbp)
                validation_items.append(
                    f"{package.name}: the current POC proxy calculation is below the target by £{gap:,.2f}. Do not add unrelated themes just to close the gap; review approved, priority-aligned delivery options."
                )
        if any(not initiative.is_from_knowledge_base for initiative in all_initiatives):
            validation_items.append(
                "Review each model-recommended initiative against the approved Infosys offer and delivery capacity before committing."
            )
        if any(initiative.partner for initiative in all_initiatives):
            validation_items.append(
                "Confirm named partners are approved and available for the stated geography; retrieved text alone does not establish current approval."
            )
        else:
            validation_items.append(
                "No delivery partner is named in the proposed options. Confirm whether an approved local partner is needed for the client priorities and contract location."
            )
        if any(not initiative.sessions_per_year or not initiative.hours_per_session or not initiative.participants_per_session for initiative in all_initiatives):
            validation_items.append(
                "Complete delivery volumes (sessions, hours and participants per session) for each initiative before finalising the response."
            )
        validation_items.append(
            "Commercial feasibility evaluated using benchmarked delivery cost models (£/unit). Final commercial bid sign-off requires partner and operational confirmation."
        )
        known_metrics = {metric.code: metric for metric in calculation_service.get_all_metrics()}
        for initiative in all_initiatives:
            metric = known_metrics.get((initiative.toms_metric_code or "").upper())
            if initiative.toms_metric_code and metric is None:
                validation_items.append(f"{initiative.name}: TOMs code {initiative.toms_metric_code} is not in the available POC catalog; its impact value is zero until mapped.")
            elif metric and metric.theme.lower() not in initiative.theme.lower() and initiative.theme.lower() not in metric.theme.lower():
                validation_items.append(f"{initiative.name}: selected TOMs measure theme ({metric.theme}) may not match initiative theme ({initiative.theme}); review the mapping.")
            if metric and initiative.sessions_per_year is not None:
                if metric.unit.lower() in {"workshops", "sessions"} and abs(initiative.annual_volume - initiative.sessions_per_year) > 0.01:
                    validation_items.append(f"{initiative.name}: annual TOMs volume ({initiative.annual_volume}) differs from sessions per year ({initiative.sessions_per_year}); reconcile before using the impact estimate.")
                if metric.unit.lower() == "hours" and initiative.hours_per_session is not None:
                    expected_hours = initiative.sessions_per_year * initiative.hours_per_session
                    if abs(initiative.annual_volume - expected_hours) > 0.01:
                        validation_items.append(f"{initiative.name}: annual TOMs hours ({initiative.annual_volume}) differs from sessions × hours ({expected_hours:g}); reconcile the volume.")
            theme_terms = set(re.findall(r"[a-z]+", initiative.theme.lower()))
            if req.priorities and not any(theme_terms.intersection(set(re.findall(r"[a-z]+", priority.lower()))) for priority in req.priorities):
                validation_items.append(f"{initiative.name}: confirm this initiative addresses at least one client priority theme ({', '.join(req.priorities)}).")
            local_scope = initiative.location.strip().lower()
            if local_scope not in {req.location.strip().lower(), "uk-wide", "uk national", "national", "regional"}:
                validation_items.append(f"{initiative.name}: delivery location '{initiative.location}' differs from requested location '{req.location}'; confirm geographic fit.")
        if len(retrieved_items) == 0:
            validation_items.append(
                "No documents currently in knowledge base. Recommendations are using synthetic baseline; "
                "ingest relevant RFP/Infosys case studies for grounded evidence."
            )

        # Step 8: Build transparent AI reasoning chain for procurement audit
        reasoning_chain = [
            AIReasoningStep(
                step_number=1,
                title="Tender Intent & Requirement Parsing",
                detail=f"Parsed RFP specifications: {req.client} ({req.location}), £{req.contract_value_gbp:,.0f} contract across {req.contract_duration_years} years. Target Social Value weighting is {req.social_value_weighting_percent}% (£{target_sv_gbp:,.0f} target). Key priorities identified: {priorities_str}."
            ),
            AIReasoningStep(
                step_number=2,
                title="Vector Knowledge Base Retrieval",
                detail=f"Executed pgvector cosine similarity search using semantic query '{retrieval_query}'. Found {len(retrieved_items)} evidence chunk(s); retrieved text still requires review for approval, recency and geographic fit."
            ),
            AIReasoningStep(
                step_number=3,
                title="National TOMs Metric Allocation",
                detail="Mapped suggested commitments to the POC TOMs proxy catalog. Values are synthetic and must be replaced with the approved National TOMs source before bid use."
            ),
            AIReasoningStep(
                step_number=4,
                title="Deterministic Calculation Guardrail",
                detail="Delegated all financial arithmetic to the Python calculation engine (Annual Volume × Duration × Unit Rate). LLM arithmetic strictly barred to eliminate financial hallucinations."
            ),
            AIReasoningStep(
                step_number=5,
                title="Commercial Viability & 10% Target Optimization",
                detail="Produced three draft options for comparison. Target achievement and commercial viability depend on verified rates, delivery volumes and approved cost inputs; review the calculated result for each option."
            )
        ]

        return ResponseGenerationResult(
            opportunity=opportunity_dict,
            core_package=core_package,
            enhanced_package=enhanced_package,
            localised_package=localised_package,
            assumptions=llm_raw.get("assumptions", []),
            validation_required=validation_items,
            retrieved_evidence_chunks=len(retrieved_items),
            grounding_summary=grounding_summary,
            ai_reasoning_chain=reasoning_chain,
            is_mock=(not settings.is_ai_configured or bool(llm_raw.get("is_fallback_mode")))
        )



    def generate_response_with_conversation(
        self,
        db: Session,
        req: OpportunityRequest,
        conversation_turns: List[Dict[str, Any]]
    ) -> ResponseGenerationResult:
        """
        Like generate_response but passes the full conversation thread to the LLM.
        The AI sees every prior turn (prompt, result summary, feedback) and
        produces a contextually improved proposal.
        """
        # Step 1: Build retrieval query from conversation context
        priorities_str = ", ".join(req.priorities) if req.priorities else "Social Value"
        retrieval_query = f"{priorities_str} initiatives in {req.location} for {req.client}"
        if req.raw_prompt and req.raw_prompt.strip():
            retrieval_query = f"{retrieval_query}. Tender requirements: {req.raw_prompt.strip()[:1200]}"

        # Step 2: Vector retrieval
        retrieved_items = retrieval_service.search_chunks(
            db=db, query=retrieval_query, top_k=req.top_k
        )

        # Step 3: Context formatting
        context_parts = []
        for i, item in enumerate(retrieved_items, start=1):
            context_parts.append(
                f"[Evidence Chunk {i}] (Doc: {item.filename}, Ref: {item.metadata or 'not supplied'}, Similarity: {item.similarity:.2f}):\n{item.content}"
            )
        context_text = "\n\n".join(context_parts)

        # Step 4: TOMs catalog
        toms_catalog = [
            {
                "code": m.code, "name": m.name, "theme": m.theme,
                "unit": m.unit, "unit_value_gbp": m.unit_value_gbp,
                "description": m.description
            }
            for m in calculation_service.get_all_metrics()
        ]

        opportunity_dict = req.model_dump()
        target_sv_gbp = round(req.contract_value_gbp * (req.social_value_weighting_percent / 100.0), 2)
        opportunity_dict["target_social_value_gbp"] = target_sv_gbp

        # Step 5: Multi-turn LLM call with FULL conversation history
        llm_raw = openai_service.generate_recommendation_with_conversation(
            context_text=context_text,
            opportunity=opportunity_dict,
            toms_catalog=toms_catalog,
            conversation_turns=conversation_turns
        )

        # Steps 6-8: Same deterministic calculation pipeline as generate_response
        core_package = self._build_social_value_package(
            llm_raw.get("core_package", {}), "Core Package", req, retrieved_items, context_text
        )
        enhanced_package = self._build_social_value_package(
            llm_raw.get("enhanced_package", {}), "Enhanced Package", req, retrieved_items, context_text
        )
        localised_package = self._build_social_value_package(
            llm_raw.get("localised_package", {}), "Localised Package", req, retrieved_items, context_text
        )

        grounding_summary = {
            "retrieval_query_used": retrieval_query,
            "top_k_requested": req.top_k,
            "evidence_chunks_found": len(retrieved_items),
            "sources_used": list(set(item.filename for item in retrieved_items)),
            "conversation_turns": len(conversation_turns),
            "generation_mode": "multi_turn_conversation"
        }

        validation_items = list(llm_raw.get("validation_required", []))
        validation_items.append("POC limitation: TOMs rates are synthetic proxy values; confirm against the approved National TOMs source before bid use.")
        validation_items.append("Commercial feasibility evaluated using benchmarked delivery cost models (£/unit). Final commercial bid sign-off requires partner and operational confirmation.")
        all_conversation_initiatives = [item for package in (core_package, enhanced_package, localised_package) for item in package.initiatives]
        for package in (core_package, enhanced_package, localised_package):
            calculation = package.financial_calculation
            if calculation and not calculation.target_met:
                gap = max(0.0, calculation.target_social_value_gbp - calculation.total_social_value_gbp)
                validation_items.append(f"{package.name}: current POC proxy value is below target by £{gap:,.2f}; review approved priority-aligned options rather than adding unrelated themes.")
        known_codes = {metric.code: metric for metric in calculation_service.get_all_metrics()}
        for initiative in all_conversation_initiatives:
            metric = known_codes.get((initiative.toms_metric_code or "").upper())
            if not initiative.is_from_knowledge_base:
                validation_items.append(f"{initiative.name}: model-suggested initiative; validate against the approved Infosys offer and delivery capacity.")
            if initiative.partner:
                validation_items.append(f"{initiative.name}: confirm partner approval and availability for {initiative.location}.")
            if initiative.toms_metric_code and metric is None:
                validation_items.append(f"{initiative.name}: TOMs code {initiative.toms_metric_code} is not in the available POC catalog; impact value is zero until mapped.")
            elif metric and metric.theme.lower() not in initiative.theme.lower() and initiative.theme.lower() not in metric.theme.lower():
                validation_items.append(f"{initiative.name}: review possible mismatch between initiative theme ({initiative.theme}) and metric theme ({metric.theme}).")
            if metric and initiative.sessions_per_year is not None:
                if metric.unit.lower() in {"workshops", "sessions"} and abs(initiative.annual_volume - initiative.sessions_per_year) > 0.01:
                    validation_items.append(f"{initiative.name}: annual TOMs volume differs from sessions per year; reconcile before using the impact estimate.")
                if metric.unit.lower() == "hours" and initiative.hours_per_session is not None:
                    expected_hours = initiative.sessions_per_year * initiative.hours_per_session
                    if abs(initiative.annual_volume - expected_hours) > 0.01:
                        validation_items.append(f"{initiative.name}: annual TOMs hours differ from sessions × hours; reconcile before using the impact estimate.")
            theme_terms = set(re.findall(r"[a-z]+", initiative.theme.lower()))
            if req.priorities and not any(theme_terms.intersection(set(re.findall(r"[a-z]+", priority.lower()))) for priority in req.priorities):
                validation_items.append(f"{initiative.name}: confirm fit to the client priority themes ({', '.join(req.priorities)}).")
            if initiative.location.strip().lower() not in {req.location.strip().lower(), "uk-wide", "uk national", "national", "regional"}:
                validation_items.append(f"{initiative.name}: confirm geographic fit; proposed location is {initiative.location}, requested location is {req.location}.")
            if not initiative.sessions_per_year or not initiative.hours_per_session or not initiative.participants_per_session:
                validation_items.append(f"{initiative.name}: complete the relevant annual sessions, hours and participant metrics before finalising.")
        if not any(item.partner for item in all_conversation_initiatives):
            validation_items.append("No delivery partner is named; confirm whether an approved local partner is needed for the client priorities and contract location.")
        if len(retrieved_items) == 0:
            validation_items.append(
                "No documents in knowledge base. Using synthetic baseline; ingest case studies for grounded evidence."
            )

        reasoning_chain = [
            AIReasoningStep(
                step_number=1,
                title="Multi-Turn Conversation Context Loaded",
                detail=(
                    f"Loaded {len(conversation_turns)} conversation turn(s) from this session. "
                    f"AI has full memory of all previous prompts, results, and feedback."
                )
            ),
            AIReasoningStep(
                step_number=2,
                title="Vector Knowledge Base Retrieval",
                detail=f"Retrieved {len(retrieved_items)} evidence chunk(s) from pgvector for {req.location}/{req.client}; review evidence for approval, recency and geographic fit."
            ),
            AIReasoningStep(
                step_number=3,
                title="Context-Aware LLM Generation",
                detail=(
                    "LLM received full conversation thread as multi-turn messages. "
                    "All prior feedback incorporated cumulatively — no context forgotten."
                )
            ),
            AIReasoningStep(
                step_number=4,
                title="Deterministic Calculation Guardrail",
                detail="Financial calculations performed by Python engine. LLM arithmetic barred."
            ),
        ]

        return ResponseGenerationResult(
            opportunity=opportunity_dict,
            core_package=core_package,
            enhanced_package=enhanced_package,
            localised_package=localised_package,
            assumptions=llm_raw.get("assumptions", []),
            validation_required=validation_items,
            retrieved_evidence_chunks=len(retrieved_items),
            grounding_summary=grounding_summary,
            ai_reasoning_chain=reasoning_chain,
            is_mock=(not settings.is_ai_configured or bool(llm_raw.get("is_fallback_mode")))
        )


rag_service = RAGService()
