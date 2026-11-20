"""
Initiative Generator (scope §6): form -> prompt built from tables + rules -> AI proposes
initiatives and units -> code values and checks them. Cost stays blank.
"""
import json
from pathlib import Path

from app.knowledge import load_initiative_types, load_tables
from app.services.initiative_valuation import (
    FRAMEWORK_VERSIONS,
    TenderForm,
    headcount_capacity,
    localised_proxy,
    value_initiatives,
)
from app.services.llm_client import complete_json_with_source

RULES = (Path(__file__).resolve().parent.parent / "knowledge" / "rules.md").read_text(encoding="utf-8")

OUTPUT_CONTRACT = """
Return JSON only, exactly this shape:
{
  "initiatives": [
    {
      "name": "Short initiative title",
      "type": "PAT-01",
      "theme": "One of the tender themes",
      "description": "What is delivered, where, for whom — no numbers",
      "attribution": "Infosys" or "Partner-led",
      "partner": "Partner name or null",
      "macs": ["2.2", "2.3"],
      "no_tom_reason": null,
      "lines": [
        {"measure": "NT8", "units": 864, "people": null, "basis": "12 sessions x 3 hrs x 8 staff x 3 years"}
      ],
      "done_before": [
        {"id": "INI-17", "shared_mac": "2.2", "shared_measures": ["NT10"],
         "why": "Both place apprentices from under-represented groups into contract roles"}
      ],
      "bid_paragraph": "First-draft paragraph, no £ figures",
      "questions": ["Question Infosys must answer before committing"]
    }
  ]
}
Propose 5 to 8 initiatives. Units are whole-of-contract totals in the measure's unit.
Quantities live only in "lines". Never put a number of people, weeks, hours or pounds in
"description" or "bid_paragraph": the tool writes those from the lines, so a figure in your
prose would disagree with the table the moment anyone changes a volume. Write "recruit people
who have been out of work for a year or more", not "recruit 40 people". A line's "units" and
"people" must agree with each other and with its "basis".
Size the package to the target. "roles_the_whole_contract_could_fund" is what the contract could
pay for if every pound went on local wages, so the people committed across all the employment
measures must come to a fraction of it — the contract has a service to deliver as well.
Claim each measure once across the whole package, and supply-chain spend once however it is
sliced: NT14, NT18 and NT19 describe the same pot of money, not three separate ones.
"type" is a label only: after deciding the initiative, give the id of the INITIATIVE TYPES entry it
clearly is, or null. Never change, add or drop an initiative to fit that list.
"macs" are the criteria this initiative claims, from the MEASURE-MAC MAP.
"no_tom_reason" is set only when "lines" is empty: why no TOM measure fits (rule A4).
"done_before" cites INFOSYS TRACK RECORD entries by id, or is [] when nothing serves the
same outcome. A citation that shares neither a criterion nor a measure will be dropped.
"""


def measure_mac_rows(tables: dict, framework: str | None) -> list[dict]:
    """The Measure-MAC map for one framework, or all of it when the tender does not name one."""
    rows = tables.get("measure_mac") or []
    wanted = FRAMEWORK_VERSIONS.get(str(framework or "").strip().upper())
    out = []
    for r in rows:
        version = str(r.get("Framework version") or "")
        if wanted and version != wanted:
            continue
        if str(r.get("MAC") or "—") == "—":
            continue  # not scored under this framework; the AI only needs the links that exist
        # "Why" is the reviewer's justification for the row, not something the AI needs to
        # choose a criterion — and across three frameworks it is half the prompt.
        row = {"measure": r.get("Measure code"), "mac": r.get("MAC"),
               "strength": r.get("Strength"), "criterion": r.get("Criterion it serves")}
        if not wanted:
            row["framework"] = version
        out.append(row)
    return out


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
        # Without a sense of scale the AI proposes headcounts the contract could never pay for,
        # and the package comes back worth more than the contract itself.
        "roles_the_whole_contract_could_fund": round(capacity) if (capacity := headcount_capacity(tables, form)) else None,
        "region": form.region,
        "duration_years": form.duration_years,
        "themes": form.themes,
    }
    if form.client:
        tender["client"] = form.client
    if form.framework:
        tender["framework"] = form.framework
    if form.brief:
        tender["client_brief"] = form.brief
    # "id" and "what" are what make a citation checkable: without them the AI cannot say
    # which past initiative it means, or judge whether it served the same outcome.
    track = [{"id": i["id"], "name": i["name"], "what": str(i.get("what") or "")[:200],
              "mac": i.get("mac"), "measures": i.get("measures")}
             for i in tables["initiative_library"]]
    mac_map = measure_mac_rows(tables, form.framework)
    user = "\n\n".join(
        [
            "TENDER:\n" + json.dumps(tender, indent=1),
            "VALID TOM MEASURES:\n" + json.dumps(measures, indent=1),
            "INFOSYS TRACK RECORD (already committed on past contracts — cite by id, never re-propose):\n"
            + json.dumps(track, indent=1, default=str),
        ]
        + [
            "INITIATIVE TYPES (labels for the \"type\" field only — not a menu of what to propose):\n"
            + json.dumps([{"id": t["id"], "name": t["name"]} for t in load_initiative_types().values()], indent=1)
        ]
        + ([f"MEASURE-MAC MAP:\n{json.dumps(mac_map, indent=1, default=str)}"] if mac_map else [])
        + ([f"INTERVENTION PATTERNS:\n{json.dumps(tables['patterns'], indent=1, default=str)}"] if tables.get("patterns") else [])
        + ([f"INFOSYS CAPABILITY PROFILE:\n{json.dumps(tables['capability'], indent=1, default=str)}"] if tables.get("capability") else [])
        + ([
            "HOW INFOSYS WRITES A MEASURABLE COMMITMENT (house style from a live contract scorecard — "
            "match this level of specificity, do not reuse these commitments):\n"
            + json.dumps(tables["wording"], indent=1, default=str)
        ] if tables.get("wording") else [])
    )
    return RULES + "\n" + OUTPUT_CONTRACT, user


def apply_initiative_types(result: dict, ai_output: dict) -> None:
    """Rule D3: the Infosys-fit rating comes from the curated type, never from the AI's own words.

    An unknown or missing type leaves the rating empty, so the screen says it is unassessed.
    """
    types = load_initiative_types()
    raw = [r for r in (ai_output.get("initiatives") or [])]
    for i, ini in enumerate(result.get("initiatives") or []):
        source = raw[i] if i < len(raw) and isinstance(raw[i], dict) else {}
        type_id = str(source.get("type") or "").strip().upper()
        known = types.get(type_id)
        if type_id and not known:
            result["checks"].append(f"{ini['name']}: unknown initiative type '{type_id}' ignored; Infosys fit not assessed.")
        ini["type"] = {"id": known["id"], "name": known["name"], "fit": known["fit"], "reason": known["reason"],
                       "terms": known["terms"]} if known else None


def generate(form: TenderForm) -> dict:
    tables = load_tables()
    system, user = build_prompt(form, tables)
    ai_output, source = complete_json_with_source(system, user)
    result = value_initiatives(ai_output, tables, form)
    apply_initiative_types(result, ai_output)
    result["form"] = {**form.__dict__, "target_gbp": form.target_gbp}
    result["model"] = source  # e.g. "azure/gpt-4.1-mini": which provider answered after any fallback
    return result
