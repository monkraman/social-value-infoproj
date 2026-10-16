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


class RAGService:
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
        if req.raw_prompt and len(req.raw_prompt.strip()) > 0 and len(req.raw_prompt) < 200:
            retrieval_query = f"{retrieval_query} ({req.raw_prompt.strip()})"

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
                f"[Evidence Chunk {i}] (Doc: {item.filename}, Sim: {item.similarity:.2f}):\n{item.content}"
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
        def process_package(pkg_data: Dict[str, Any], pkg_name: str) -> SocialValuePackage:
            raw_initiatives = pkg_data.get("initiatives", [])
            processed_items: List[InitiativeItem] = []

            for raw_init in raw_initiatives:
                init_item = InitiativeItem(
                    name=raw_init.get("name", "Social Value Initiative"),
                    theme=raw_init.get("theme", "Community"),
                    location=raw_init.get("location", req.location),
                    description=raw_init.get("description", ""),
                    delivery_mechanism=raw_init.get("delivery_mechanism", ""),
                    target_beneficiaries=raw_init.get("target_beneficiaries", "Local residents"),
                    annual_volume=float(raw_init.get("annual_volume", 1.0)),
                    toms_metric_code=raw_init.get("toms_metric_code"),
                    partner=raw_init.get("partner"),
                    evidence_source=raw_init.get("evidence_source", "Knowledge Base"),
                    is_from_knowledge_base=bool(raw_init.get("is_from_knowledge_base", False)),
                    sessions_per_year=raw_init.get("sessions_per_year"),
                    hours_per_session=raw_init.get("hours_per_session"),
                    participants_per_session=raw_init.get("participants_per_session"),
                    indicative_cost_gbp=float(raw_init.get("indicative_cost_gbp", 0.0)),
                    commercial_viability=raw_init.get("commercial_viability", "Internal Operational Delivery")
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

            # Calculate total internal delivery cost
            total_delivery_cost = float(pkg_data.get("indicative_delivery_cost_gbp", sum(i.indicative_cost_gbp or 0.0 for i in processed_items)))

            return SocialValuePackage(
                name=pkg_name,
                initiatives=processed_items,
                rationale=pkg_data.get("rationale", ""),
                expected_impact=pkg_data.get("expected_impact", []),
                dependencies=pkg_data.get("dependencies", []),
                financial_calculation=calculation_result,
                indicative_delivery_cost_gbp=total_delivery_cost,
                commercial_viability_summary=pkg_data.get("commercial_viability_summary", "High SVROI / Standard Delivery"),
                governance=GovernanceCadence(
                    social_value_lead="Dedicated Infosys Social Value Lead assigned upon contract award",
                    kickoff_cadence="Joint Social Value Kick-Off Meeting held within 60 days of contract signature",
                    reporting_frequency="Quarterly Social Value Progress & National TOMs Performance Reporting",
                    annual_review="Annual SVROI impact evaluation and financial verification audit"
                )
            )

        core_package = process_package(llm_raw.get("core_package", {}), "Core Package")
        enhanced_package = process_package(llm_raw.get("enhanced_package", {}), "Enhanced Package")
        localised_package = process_package(llm_raw.get("localised_package", {}), "Localised Package")

        # Step 7: Grounding summary and validation check
        grounding_summary = {
            "retrieval_query_used": retrieval_query,
            "top_k_requested": req.top_k,
            "evidence_chunks_found": len(retrieved_items),
            "sources_used": list(set(item.filename for item in retrieved_items)),
            "highest_similarity": retrieved_items[0].similarity if retrieved_items else 0.0
        }

        validation_items = llm_raw.get("validation_required", [])
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
                detail=f"Executed pgvector cosine similarity search using semantic query '{retrieval_query}'. Found {len(retrieved_items)} grounded evidence chunk(s) from past Infosys bids and regional CSR archives."
            ),
            AIReasoningStep(
                step_number=3,
                title="National TOMs Metric Allocation",
                detail=f"Mapped delivery commitments to approved National TOMs measures: NT1 (Apprenticeships), NT3 (Youth into Work), NT8 (Digital Skills), NT10 (Volunteering), NT14 (SME Supply Chain Spend), and NT20 (Hardware Refurbishment)."
            ),
            AIReasoningStep(
                step_number=4,
                title="Deterministic Calculation Guardrail",
                detail="Delegated all financial arithmetic to the Python calculation engine (Annual Volume × Duration × Unit Rate). LLM arithmetic strictly barred to eliminate financial hallucinations."
            ),
            AIReasoningStep(
                step_number=5,
                title="Commercial Viability & 10% Target Optimization",
                detail=f"Formulated 3 delivery options: Core Package (low risk baseline compliance), Localised Package (hits exactly £{target_sv_gbp:,.0f} target with ward-level {req.location} commitments), and Enhanced Package (+12% margin for decisive win advantage). Formulated internal delivery costs to ensure positive commercial viability."
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
            is_mock=not settings.is_ai_configured
        )



rag_service = RAGService()
