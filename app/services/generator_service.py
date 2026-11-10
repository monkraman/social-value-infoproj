"""
Initiative Generator (scope §6): form -> prompt built from tables + rules -> AI proposes
initiatives and units -> code values and checks them. Cost stays blank.
"""
import json
from pathlib import Path

from app.knowledge import load_tables
from app.services.initiative_valuation import TenderForm, localised_proxy, value_initiatives
from app.services.llm_client import complete_json

RULES = (Path(__file__).resolve().parent.parent / "knowledge" / "rules.md").read_text(encoding="utf-8")

OUTPUT_CONTRACT = """
Return JSON only, exactly this shape:
{
  "initiatives": [
    {
      "name": "Short initiative title",
      "theme": "One of the tender themes",
      "description": "What is delivered, where, for whom",
      "attribution": "Infosys" or "Partner-led",
      "partner": "Partner name or null",
      "lines": [
        {"measure": "NT8", "units": 864, "people": null, "basis": "12 sessions x 3 hrs x 8 staff x 3 years"}
      ],
      "bid_paragraph": "First-draft paragraph, no £ figures",
      "questions": ["Question Infosys must answer before committing"]
    }
  ]
}
Propose 5 to 8 initiatives. Units are whole-of-contract totals in the measure's unit.
"""


def build_prompt(form: TenderForm, tables: dict) -> tuple[str, str]:
    """System = rules + output contract. User = the tender and the tables the AI may draw on."""
    measures = []
    for m in tables["measures"]:
        proxy, _ = localised_proxy(m["code"], tables, form.region, form.industry)
        # Proxies are given only so the AI can size units to the target; the code recomputes every £.
        measures.append({"code": m["code"], "theme": m["theme"], "name": m["name"], "unit": m["unit"],
                         "proxy_per_unit_for_sizing": round(proxy, 4) if proxy else None, "unit_guidance": m["unit_guidance"]})
    tender = {
        "company": form.company,
        "contract_value_gbp": form.bid_amount_gbp,
        "social_value_percent": form.sv_percent,
        "target_value_gbp": form.target_gbp,
        "region": form.region,
        "duration_years": form.duration_years,
        "themes": form.themes,
    }
    library = [{k: i[k] for k in ("name", "pillar", "mac", "attribution", "measures")} for i in tables["initiative_library"]]
    user = "\n\n".join(
        [
            "TENDER:\n" + json.dumps(tender, indent=1),
            "VALID TOM MEASURES:\n" + json.dumps(measures, indent=1),
            "REFERENCE INITIATIVES (shapes Infosys has used before):\n" + json.dumps(library, indent=1),
        ]
        + ([f"INTERVENTION PATTERNS:\n{json.dumps(tables['patterns'], indent=1, default=str)}"] if tables.get("patterns") else [])
        + ([f"INFOSYS CAPABILITY PROFILE:\n{json.dumps(tables['capability'], indent=1, default=str)}"] if tables.get("capability") else [])
    )
    return RULES + "\n" + OUTPUT_CONTRACT, user


def generate(form: TenderForm) -> dict:
    tables = load_tables()
    system, user = build_prompt(form, tables)
    ai_output = complete_json(system, user)
    result = value_initiatives(ai_output, tables, form)
    result["form"] = {**form.__dict__, "target_gbp": form.target_gbp}
    return result
