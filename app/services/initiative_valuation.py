"""
The code layer (scope §2): values AI-proposed initiatives and enforces the rules.

The AI proposes initiatives and *units* only. Everything in £ is computed here from
the tables (app/knowledge/tables.json): units × (localised) proxy. Rule references
(A-xx) point to the Assumptions sheet of the Monk Spaces workbook.

Pure functions — no database, no network — so every rule is unit-tested.
"""
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# A-07: one measure per activity. Within an initiative only the first of these counts.
EMPLOYMENT_MEASURES = {"NT1", "NT3", "NT4", "NT5", "NT6", "NT76", "NT10"}
# A-06: barrier-group recruitment, capped at 1 FTE-year per person.
BARRIER_MEASURES = {"NT3", "NT4", "NT5", "NT6", "NT76"}
# A-13: carbon counts only beyond the measured 2.4%/yr baseline -> conditional until confirmed.
CARBON_MEASURES = {"NT31", "NT31a"}
# Units are £ spend through the supply chain; cannot exceed the contract value.
SPEND_MEASURES = {"NT14", "NT18", "NT19"}

COUNTED = "Counted"
CONDITIONAL = "Conditional"
ALTERNATIVE = "Alternative"
NOT_VALUED = "Not valued"

# Rule 2: the AI must never supply a £ figure. Any such key is dropped.
_MONEY_KEY = re.compile(r"(value|gbp|cost|price|proxy|£)", re.IGNORECASE)
_MONEY_TEXT = re.compile(r"£\s?\d[\d,.]*\s?(k|m|bn|million|billion)?\b", re.IGNORECASE)

ALWAYS_ASK = "Confirm cost, delivery owner and evidence before committing."

# The "Framework version" written in the Measure-MAC sheet, by the id the frontend sends.
FRAMEWORK_VERSIONS = {
    "PPN0620": "SV Model 06/20",
    "PPN002": "SV Model 2025 (PPN 002)",
    "PPN026": "SV Model 2027 (PPN 026)",
}

_MEASURE_CODE = re.compile(r"NT\d+[a-z]?", re.IGNORECASE)


def _measure_codes(raw: Any) -> set:
    """TOM codes from a track-record 'measures' cell, which is a list or its string form."""
    items = _MEASURE_CODE.findall(raw) if isinstance(raw, str) else (raw or [])
    return {str(c).strip() for c in items if _MEASURE_CODE.fullmatch(str(c).strip())}


def _mac(raw: Any) -> str:
    """'MAC 2.2' -> '2.2'. Returns '' for the em dash the sheets use for 'none'."""
    text = re.sub(r"^mac\s*", "", str(raw or "").strip(), flags=re.IGNORECASE).strip()
    return "" if text in ("", "—", "-", "None") else text


def mac_index(tables: dict, framework: Optional[str]) -> Dict[str, List[Tuple[str, str]]]:
    """measure code -> [(mac, strength)] under `framework`, from the Measure-MAC map."""
    wanted = FRAMEWORK_VERSIONS.get(str(framework or "").strip().upper())
    index: Dict[str, List[Tuple[str, str]]] = {}
    for row in tables.get("measure_mac") or []:
        if wanted and str(row.get("Framework version") or "") != wanted:
            continue
        code, mac = str(row.get("Measure code") or "").strip(), _mac(row.get("MAC"))
        if code and mac:
            index.setdefault(code, []).append((mac, str(row.get("Strength") or "Supporting")))
    return index


def _check_citations(
    cites: Any, track: Dict[str, dict], proposed: set, claimed: List[str],
    index: Dict[str, List[Tuple[str, str]]], name: str, checks: List[str],
) -> List[dict]:
    """Rule D2: keep a citation only where the data shows a shared outcome.

    Three signals, all from the tables — never from how alike the wording is:
      a) the past initiative used one of the measures now proposed;
      b) its own criterion is one this initiative claims (same framework numbering);
      c) its measures serve one of the claimed criteria under this framework.
    """
    kept: List[dict] = []
    for cite in cites or []:
        if not isinstance(cite, dict):
            continue
        ident = str(cite.get("id") or "").strip()
        past = track.get(ident)
        if past is None:
            checks.append(f"{name}: dropped citation '{ident or '(no id)'}' — not in the track record.")
            continue
        past_measures = _measure_codes(past.get("measures"))
        via_measure = bool(proposed & past_measures)
        via_own_mac = _mac(past.get("mac")) in claimed if claimed else False
        via_map = any(mac in claimed for code in past_measures for mac, _ in index.get(code, ()))
        if not (via_measure or via_own_mac or via_map):
            checks.append(
                f"{name}: dropped citation {ident} ({past.get('name')}) — it shares no criterion "
                "and no measure with this initiative (D2)."
            )
            continue
        kept.append({
            "id": ident,
            "name": past.get("name"),
            "what": past.get("what"),
            "mac": past.get("mac"),
            "measures": sorted(past_measures),
            "why": str(cite.get("why") or ""),
        })
    return kept[:3]  # D4


@dataclass
class TenderForm:
    company: str
    bid_amount_gbp: float
    sv_percent: float
    region: str
    duration_years: float
    themes: List[str] = field(default_factory=list)
    industry: Optional[str] = None
    client: Optional[str] = None
    # "PPN0620", "PPN002" or "PPN026". Selects the rows of the Measure-MAC map the AI is shown;
    # when it is None the whole map is passed and the AI takes the framework from the brief.
    framework: Optional[str] = None
    # The buyer's own words (prompt mode). Gives the AI context; never used for any number.
    brief: Optional[str] = None

    @property
    def target_gbp(self) -> float:
        return round(self.bid_amount_gbp * self.sv_percent / 100.0, 2)


def localised_proxy(code: str, tables: dict, region: str, industry: Optional[str]) -> Tuple[Optional[float], str]:
    """Proxy £ per unit for `code`, localised where the TOM System requires it (A-03)."""
    measure = next((m for m in tables["measures"] if m["code"] == code), None)
    if measure is None:
        return None, "not an Open Access measure"
    if not measure.get("localised"):
        return measure["proxy_gbp"], "national proxy"

    reg = next((r for r in tables["regions"] if r["region"] == region), None)
    if reg is None:
        return measure["proxy_gbp"], f"national proxy (region '{region}' not in tables)"
    if code == "NT1":
        return reg["median_wage_gbp"], f"{region} median wage"

    industry = industry or tables["settings"]["default_industry"]
    ind = next((i for i in tables["industries"] if i["industry"] == industry), None)
    if ind is None:
        return measure["proxy_gbp"], f"national proxy (industry '{industry}' not in tables)"
    nt18 = (ind["gva_multiplier"] - 1) * reg["regional_gva"]
    if code == "NT18":
        return nt18, f"{region} GVA × {industry} multiplier"
    if code == "NT19":
        return nt18 * tables["settings"]["nt19_factor"], f"{region} GVA × {industry} multiplier × SME factor"
    return measure["proxy_gbp"], "national proxy"


def _num(v: Any) -> Optional[float]:
    try:
        n = float(v)
    except (TypeError, ValueError):
        return None
    return n if n == n else None  # reject NaN


def _strip_money(obj: dict, where: str, checks: List[str]) -> dict:
    clean = {}
    for k, v in obj.items():
        if _MONEY_KEY.search(k):
            checks.append(f"{where}: AI returned '{k}' — ignored; values come from the tables only.")
            continue
        clean[k] = v
    return clean


def value_initiatives(ai_output: dict, tables: dict, form: TenderForm) -> Dict[str, Any]:
    """Value the AI's proposed initiatives against the tables and apply the rules."""
    checks: List[str] = []
    measures = {m["code"]: m for m in tables["measures"]}
    track = {str(i.get("id") or "").strip(): i for i in tables.get("initiative_library") or []}
    index = mac_index(tables, form.framework)
    initiatives_out = []
    totals = {"infosys_gbp": 0.0, "partner_gbp": 0.0, "conditional_gbp": 0.0}

    for idx, raw in enumerate(ai_output.get("initiatives") or [], start=1):
        ini = _strip_money(raw if isinstance(raw, dict) else {}, f"Initiative {idx}", checks)
        name = str(ini.get("name") or f"Initiative {idx}")
        partner_led = str(ini.get("attribution", "")).lower().startswith("partner")
        questions = [str(q) for q in (ini.get("questions") or []) if str(q).strip()]

        paragraph = str(ini.get("bid_paragraph") or "")
        if _MONEY_TEXT.search(paragraph):
            paragraph = _MONEY_TEXT.sub("[value]", paragraph)
            checks.append(f"{name}: £ figures in the AI's paragraph were removed; use the calculated value.")

        lines_out = []
        employment_counted = False
        for raw_line in ini.get("lines") or []:
            line = _strip_money(raw_line if isinstance(raw_line, dict) else {}, name, checks)
            code = str(line.get("measure") or "").strip().upper()
            if code == "NT31A":
                code = "NT31a"  # official casing
            units = _num(line.get("units"))
            people = _num(line.get("people"))
            out = {
                "measure": code,
                "measure_name": measures.get(code, {}).get("name"),
                "unit": measures.get(code, {}).get("unit"),
                "units": units,
                "basis": str(line.get("basis") or ""),
                "proxy_gbp": None,
                "proxy_basis": None,
                "value_gbp": 0.0,
                "status": COUNTED,
                "note": "",
            }
            lines_out.append(out)

            if code not in measures:
                out.update(status=NOT_VALUED, note="Not an Open Access TOM measure.")
                continue
            if units is None or units <= 0:
                out.update(status=NOT_VALUED, note="No usable quantity.")
                continue

            # Caps that keep units realistic (A-06, NT1 unit guidance, contract size).
            if code in BARRIER_MEASURES and people is not None and units > people:
                out["note"] = f"Capped at 1 FTE-year per person ({people:g} people)."
                units = people
            if code == "NT1" and people is not None and units > people * form.duration_years:
                out["note"] = f"Capped at 1 FTE per person per year ({people:g} × {form.duration_years:g} yrs)."
                units = people * form.duration_years
            if code in SPEND_MEASURES and units > form.bid_amount_gbp:
                out["note"] = "Capped at the contract value."
                units = form.bid_amount_gbp
            if code in BARRIER_MEASURES | {"NT1"} and people is None:
                questions.append(f"How many people does {code} cover? FTE is capped per person.")
            out["units"] = units

            proxy, basis = localised_proxy(code, tables, form.region, form.industry)
            out["proxy_gbp"], out["proxy_basis"] = proxy, basis
            out["value_gbp"] = round(units * proxy, 2)

            if code in EMPLOYMENT_MEASURES:
                if employment_counted:
                    out.update(status=ALTERNATIVE, note="Same people as another measure here — shown, never added (A-07).")
                    continue
                employment_counted = True
            if code in CARBON_MEASURES:
                rate = tables["settings"]["carbon_baseline_rate"]
                out.update(status=CONDITIONAL, note=f"Counts only beyond the measured {rate:.1%}/yr baseline (A-13).")
                questions.append("What is the measured previous-year carbon baseline?")

        # A1/A2: a claimed criterion has to be reachable from a measure actually proposed.
        claimed = [m for m in (_mac(x) for x in (ini.get("macs") or [])) if m]
        proposed = {l["measure"] for l in lines_out if l["measure"] in measures}
        if index and proposed:
            served: Dict[str, str] = {}
            for code in proposed:
                for mac, strength in index.get(code, ()):
                    if served.get(mac) != "Direct":
                        served[mac] = strength
            for mac in claimed:
                if mac not in served:
                    checks.append(f"{name}: dropped claimed criterion MAC {mac} — no proposed measure serves it (A1).")
            claimed = [m for m in claimed if m in served]
            if claimed and not any(served.get(m) == "Direct" for m in claimed):
                checks.append(
                    f"{name}: only supporting links to MAC {', '.join(claimed)} — needs a direct measure to score (A2)."
                )
        done_before = _check_citations(ini.get("done_before"), track, proposed, claimed, index, name, checks)

        no_tom_reason = str(ini.get("no_tom_reason") or "").strip() or None
        if not lines_out and not no_tom_reason:
            questions.append("No TOM measure was proposed and no reason was given — confirm how this is evidenced.")

        counted = sum(l["value_gbp"] for l in lines_out if l["status"] == COUNTED)
        conditional = sum(l["value_gbp"] for l in lines_out if l["status"] == CONDITIONAL)
        totals["partner_gbp" if partner_led else "infosys_gbp"] += counted
        totals["conditional_gbp"] += conditional
        questions.append(ALWAYS_ASK)

        initiatives_out.append({
            "name": name,
            "theme": ini.get("theme"),
            "description": ini.get("description"),
            "attribution": "Partner-led" if partner_led else "Infosys",
            "partner": ini.get("partner"),
            "macs": claimed,
            "no_tom_reason": no_tom_reason,
            "done_before": done_before,
            "lines": lines_out,
            "value_gbp": round(counted, 2),
            "conditional_gbp": round(conditional, 2),
            "cost_gbp": None,  # Stage one: cost is left blank for Infosys (scope §1)
            "bid_paragraph": paragraph,
            "questions": list(dict.fromkeys(questions)),
            "status": "Proposal",
        })

    totals = {k: round(v, 2) for k, v in totals.items()}
    target = form.target_gbp
    if target > 0 and totals["infosys_gbp"] > target * 1.5:
        checks.append(
            f"Infosys value is {totals['infosys_gbp'] / target:.0%} of the target — check the units are realistic for this contract."
        )
    if not tables.get("measure_mac"):
        checks.append("Measure–MAC map not loaded yet: framework fit is not checked.")
    if not tables.get("capability"):
        checks.append("Infosys capability profile not loaded yet: capability fit is not checked.")

    return {
        "target_gbp": target,
        "totals": totals,
        "initiatives": initiatives_out,
        "checks": list(dict.fromkeys(checks)),
        "tables": {"source": tables.get("source"), "edition": tables.get("edition"), "imported_at": tables.get("imported_at")},
    }
