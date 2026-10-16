import re
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.prompt_history import PromptHistory
from app.schemas.response import (
    OpportunityRequest,
    ResponseGenerationResult
)
from app.services.rag_service import rag_service
from app.services.openai_service import openai_service
from app.core.config import settings


class PromptInterpreterService:
    """
    Interprets natural language user prompts on the backend,
    classifies intent (RFP, Navigation, or General/Non-RFP),
    records full audit history in PostgreSQL/SQLite,
    and executes RAG generation.
    """

    def interpret_and_execute(
        self,
        db: Session,
        prompt_text: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        prompt = prompt_text.strip()
        prompt_lower = prompt.lower()

        # 1. Navigation Intent Checks
        if len(prompt) < 80:
            if any(w in prompt_lower for w in ["open doc", "view doc", "show doc", "documents tab", "upload file", "see files"]):
                return self._record_and_return_nav(db, prompt, "navigation_documents", "Navigating to Knowledge Documents repository.")
            if any(w in prompt_lower for w in ["search vector", "open search", "show search", "vector search", "search tab"]):
                return self._record_and_return_nav(db, prompt, "navigation_search", "Navigating to Vector Search tool.")

        # 2. RFP Tender Specification Intent Check
        is_rfp, explanation = self._check_is_rfp_intent(prompt)

        if not is_rfp:
            # Random / Non-Tender Prompt ("harkuch prompt")
            history_record = PromptHistory(
                raw_prompt=prompt,
                intent="non_rfp",
                is_rfp_prompt=False,
                explanation=explanation,
                created_at=datetime.now(timezone.utc)
            )
            db.add(history_record)
            db.commit()

            return {
                "prompt_id": str(history_record.id),
                "is_rfp_prompt": False,
                "intent": "non_rfp",
                "explanation": explanation,
                "request": None,
                "result": None,
                "created_at": history_record.created_at.isoformat()
            }

        # 3. Parse Tender Parameters from Prompt
        req_params = self._extract_parameters(prompt)
        opportunity_request = OpportunityRequest(**req_params)

        # 4. Execute RAG Generation Pipeline
        result = rag_service.generate_response(db=db, req=opportunity_request)

        # 5. Record Full Prompt History in Database
        response_snapshot = {
            "core_total_sv": result.core_package.financial_calculation.total_social_value_gbp if result.core_package.financial_calculation else 0,
            "enhanced_total_sv": result.enhanced_package.financial_calculation.total_social_value_gbp if result.enhanced_package.financial_calculation else 0,
            "localised_total_sv": result.localised_package.financial_calculation.total_social_value_gbp if result.localised_package.financial_calculation else 0,
            "target_amount": result.opportunity.get("target_social_value_gbp", 0),
            "target_met": result.localised_package.financial_calculation.target_met if result.localised_package.financial_calculation else False
        }

        history_record = PromptHistory(
            raw_prompt=prompt,
            intent="rfp_opportunity",
            is_rfp_prompt=True,
            client_name=opportunity_request.client,
            location=opportunity_request.location,
            contract_value_gbp=opportunity_request.contract_value_gbp,
            contract_duration_years=opportunity_request.contract_duration_years,
            social_value_weighting_percent=opportunity_request.social_value_weighting_percent,
            priorities=opportunity_request.priorities,
            explanation=None,
            response_summary=response_snapshot,
            created_at=datetime.now(timezone.utc)
        )
        db.add(history_record)
        db.commit()

        return {
            "prompt_id": str(history_record.id),
            "is_rfp_prompt": True,
            "intent": "rfp_opportunity",
            "explanation": None,
            "request": opportunity_request.model_dump(),
            "result": result.model_dump(),
            "created_at": history_record.created_at.isoformat()
        }

    def _check_is_rfp_intent(self, prompt: str) -> tuple[bool, str]:
        """Detects whether prompt contains sufficient tender criteria or is an irrelevant query."""
        p = prompt.lower()

        # Specific RFP trigger terms
        has_social_value = any(term in p for term in ["social value", "sv", "toms", "national toms", "svroi", "ppn 06/20"])
        has_tender_terms = any(term in p for term in ["contract", "tender", "rfp", "bid", "procurement", "weighting", "council", "nhs"])
        has_metrics_or_val = any(term in p for term in ["£", "million", "m ", "year", "yr", "%", "target"])

        # Check for non-RFP chatter (e.g. general questions, jokes, code requests)
        is_chatter = False
        if len(prompt.split()) < 6 and not has_social_value:
            is_chatter = True
        if any(p.startswith(prefix) for prefix in ["what is ", "who is ", "tell me a ", "write a poem", "how are you", "weather in"]):
            if not has_social_value and not has_tender_terms:
                is_chatter = True

        if is_chatter or (not has_social_value and not (has_tender_terms and has_metrics_or_val)):
            return False, (
                "The submitted prompt does not contain recognized tender or Social Value parameters. "
                "To formulate an auditable bid proposal, please provide: Contract Duration (e.g. 3 years), "
                "Contract Value (e.g. £10M), Target Weighting (e.g. 10%), Client Authority/Location, and Priority Themes."
            )

        return True, ""

    UK_LOCATIONS: List[str] = [
        "Birmingham", "Manchester", "Leeds", "London", "Bristol", "Liverpool",
        "Sheffield", "Newcastle", "Glasgow", "Edinburgh", "Cardiff", "Coventry",
        "Leicester", "Nottingham", "Southampton", "Belfast", "Westminster", "Salford",
        "Bradford", "Sunderland", "Wolverhampton", "Brighton", "Plymouth", "Derby",
        "Stoke", "Hull", "York", "Reading", "Milton Keynes", "Aberdeen", "Swansea",
        "Oxford", "Cambridge", "Bath", "Exeter", "Norwich", "Dundee", "Gloucester",
        "Camden", "Hackney", "Islington", "Greenwich", "Southwark", "Croydon"
    ]

    def _extract_parameters(self, prompt: str) -> Dict[str, Any]:
        """Extracts structured tender parameters from natural language prompt."""
        p = prompt
        p_lower = p.lower()

        # 1. Contract Duration
        duration = 3
        duration_match = re.search(r'(\d+)\s*(?:-| )(?:year|yr)s?', p, re.IGNORECASE)
        if duration_match:
            try:
                duration = int(duration_match.group(1))
            except ValueError:
                duration = 3

        # 2. Contract Value (GBP)
        contract_value = 10000000.0
        val_match = re.search(r'£\s*(\d+(?:\.\d+)?)\s*(m|million|k|thousand)?', p, re.IGNORECASE)
        if val_match:
            try:
                base_val = float(val_match.group(1))
                unit = (val_match.group(2) or '').lower()
                if unit in ['m', 'million']:
                    contract_value = base_val * 1_000_000.0
                elif unit in ['k', 'thousand']:
                    contract_value = base_val * 1_000.0
                else:
                    contract_value = base_val
            except ValueError:
                contract_value = 10000000.0

        # 3. Target Weighting (%)
        weighting = 10.0
        weight_match = re.search(r'(\d+(?:\.\d+)?)\s*%\s*(?:social value|sv|weighting)?', p, re.IGNORECASE)
        if weight_match:
            try:
                weighting = float(weight_match.group(1))
            except ValueError:
                weighting = 10.0

        # 4. Client and Location Detection (Dynamic, without hardcoded Birmingham)
        client: Optional[str] = None
        location: Optional[str] = None

        # Step 4a: Check if explicit UK city/location is mentioned in prompt
        for uk_loc in self.UK_LOCATIONS:
            if re.search(r'\b' + re.escape(uk_loc) + r'\b', p, re.IGNORECASE):
                location = uk_loc
                break

        # Step 4b: Look for explicit client patterns (e.g. 'client XYZ wants')
        client_match = re.search(
            r'client\s*[:=]?\s*([A-Za-z0-9\s&\'()-]+?)(?:\s+(?:in|wants|requires|located|demands)|,|$|\.)',
            p,
            re.IGNORECASE
        )
        if client_match:
            cand = client_match.group(1).strip()
            # Strip placeholder tokens like (INSERT), [INSERT], etc.
            clean_cand = re.sub(r'[\(\[\{<]?insert[\)\]\}>]?', '', cand, flags=re.IGNORECASE).strip()
            if len(clean_cand) > 2 and clean_cand.lower() not in ["the", "a", "an", "client"]:
                client = clean_cand

        # Check for authority following for/with/to if client not found
        if not client:
            auth_match = re.search(
                r'(?:for|with|to)\s+([A-Za-z0-9\s&\'()-]+?\s+(?:City\s+Council|County\s+Council|Borough\s+Council|Council|Combined\s+Authority|Authority|NHS\s+Trust|NHS|Trust|Board|Department|Agency|Service|Constabulary|University))',
                p,
                re.IGNORECASE
            )
            if auth_match:
                cand = auth_match.group(1).strip()
                clean_cand = re.sub(r'[\(\[\{<]?insert[\)\]\}>]?', '', cand, flags=re.IGNORECASE).strip()
                if len(clean_cand) > 2:
                    client = clean_cand

        # Step 4c: Reconcile client and location
        if location and not client:
            if "nhs" in p_lower or "trust" in p_lower:
                client = f"{location} NHS Trust"
            elif "police" in p_lower:
                client = f"{location} Police Authority"
            elif "council" in p_lower or "city" in p_lower:
                client = f"{location} City Council"
            else:
                client = f"{location} City Council"

        if client and not location:
            for uk_loc in self.UK_LOCATIONS:
                if re.search(r'\b' + re.escape(uk_loc) + r'\b', client, re.IGNORECASE):
                    location = uk_loc
                    break
            if not location:
                location = client.split()[0] if len(client.split()) > 0 else "UK Regional"

        # Step 4d: Fallback only when prompt provides NO client and NO location
        # Default to generic Public Sector Authority (NOT Birmingham!)
        if not client:
            if "nhs" in p_lower or "trust" in p_lower or "hospital" in p_lower:
                client = "NHS Regional Health Trust"
                location = "UK National"
            elif any(w in p_lower for w in ["central government", "civil service", "ministry", "cabinet office"]):
                client = "Crown Commercial Service"
                location = "UK Central Government"
            else:
                client = "UK Public Sector Authority"
                location = "UK Regional"

        if not location:
            location = "UK Regional"

        # 5. Priorities / Themes Extraction
        priorities: List[str] = []
        if any(w in p_lower for w in ["digital inclusion", "digital skills", "it literacy", "broadband", "coding"]):
            priorities.append("Digital Inclusion")
        if any(w in p_lower for w in ["youth employment", "young people", "apprenticeship", "neet", "early career"]):
            priorities.append("Youth Employment")
        if any(w in p_lower for w in ["skills gap", "skills training", "workforce", "upskilling", "reskilling"]):
            priorities.append("Employment & Skills")
        if any(w in p_lower for w in ["supply chain", "sme", "vcse", "local spend", "tier 2", "local business"]):
            priorities.append("Local Supply Chain")
        if any(w in p_lower for w in ["net zero", "carbon", "green", "environment", "climate", "sustainability"]):
            priorities.append("Net Zero & Environment")
        if any(w in p_lower for w in ["healthcare", "health", "wellbeing", "mental health"]):
            priorities.append("Health & Wellbeing")
        if any(w in p_lower for w in ["stem", "school", "education"]):
            priorities.append("STEM & Education")
        if "modern slavery" in p_lower or "living wage" in p_lower:
            priorities.append("Modern Slavery & Ethics")

        # Also extract custom themes from 'address <themes>'
        address_match = re.search(r'address\s+([A-Za-z0-9\s,&/-]+?)(?:\.|\s+based\s+on|$|\s+and\s+the\s+impact)', p, re.IGNORECASE)
        if address_match:
            raw_chunk = address_match.group(1).strip()
            clean_chunk = re.sub(r'[\(\[\{<]?insert[\)\]\}>]?', '', raw_chunk, flags=re.IGNORECASE)
            parts = [s.strip().title() for s in re.split(r'[,&]|\band\b', clean_chunk) if len(s.strip()) > 3]
            for pt in parts:
                if pt not in priorities and len(priorities) < 5:
                    priorities.append(pt)

        # Standard Social Value pillars fallback if no priorities were stated in prompt
        if not priorities:
            priorities = ["Local Skills & Employment", "Local Economic Growth", "Community Wellbeing"]

        return {
            "contract_duration_years": duration,
            "contract_value_gbp": contract_value,
            "social_value_weighting_percent": weighting,
            "client": client,
            "location": location,
            "priorities": priorities,
            "raw_prompt": p
        }


    def _record_and_return_nav(self, db: Session, prompt: str, intent: str, msg: str) -> Dict[str, Any]:
        record = PromptHistory(
            raw_prompt=prompt,
            intent=intent,
            is_rfp_prompt=False,
            explanation=msg,
            created_at=datetime.now(timezone.utc)
        )
        db.add(record)
        db.commit()

        return {
            "prompt_id": str(record.id),
            "is_rfp_prompt": False,
            "intent": intent,
            "explanation": msg,
            "request": None,
            "result": None,
            "created_at": record.created_at.isoformat()
        }

    def list_history(self, db: Session, limit: int = 25) -> List[Dict[str, Any]]:
        records = db.query(PromptHistory).order_by(PromptHistory.created_at.desc()).limit(limit).all()
        return [
            {
                "id": str(r.id),
                "raw_prompt": r.raw_prompt,
                "intent": r.intent,
                "is_rfp_prompt": r.is_rfp_prompt,
                "client_name": r.client_name,
                "location": r.location,
                "contract_value_gbp": r.contract_value_gbp,
                "duration_years": r.contract_duration_years,
                "weighting_percent": r.social_value_weighting_percent,
                "priorities": r.priorities or [],
                "explanation": r.explanation,
                "response_summary": r.response_summary,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in records
        ]


prompt_interpreter_service = PromptInterpreterService()
