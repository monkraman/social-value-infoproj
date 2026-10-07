from typing import Dict, Any, List
from sqlalchemy.orm import Session

from app.schemas.response import (
    OpportunityRequest,
    ResponseGenerationResult,
    SocialValuePackage,
    InitiativeItem
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
        """
        # Step 1: Query Formulation
        priorities_str = ", ".join(req.priorities) if req.priorities else "Social Value"
        retrieval_query = f"{priorities_str} initiatives in {req.location} for {req.client}"

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
                    is_from_knowledge_base=bool(raw_init.get("is_from_knowledge_base", False))
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

            return SocialValuePackage(
                name=pkg_name,
                initiatives=processed_items,
                rationale=pkg_data.get("rationale", ""),
                expected_impact=pkg_data.get("expected_impact", []),
                dependencies=pkg_data.get("dependencies", []),
                financial_calculation=calculation_result
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

        return ResponseGenerationResult(
            opportunity=opportunity_dict,
            core_package=core_package,
            enhanced_package=enhanced_package,
            localised_package=localised_package,
            assumptions=llm_raw.get("assumptions", []),
            validation_required=validation_items,
            retrieved_evidence_chunks=len(retrieved_items),
            grounding_summary=grounding_summary,
            is_mock=not settings.is_ai_configured
        )


rag_service = RAGService()
