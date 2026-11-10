"""
Read a plain-English tender description into the Initiative Generator form.

Deterministic (no AI), so it works when the AI provider is down and always says
what it found and what it did not — the user confirms the form before generating.
"""
import re
from typing import Any, Dict, List, Optional

# City / area -> region name as used in the Localisation table.
CITY_REGION = {
    "West Midlands": ["birmingham", "coventry", "wolverhampton", "solihull", "walsall", "dudley", "stoke"],
    "North West": ["manchester", "liverpool", "salford", "bolton", "preston", "lancashire", "cheshire", "cumbria"],
    "Yorkshire and The Humber": ["leeds", "sheffield", "bradford", "hull", "york", "wakefield", "doncaster", "yorkshire"],
    "North East": ["newcastle", "sunderland", "durham", "middlesbrough", "gateshead", "northumberland", "teesside"],
    "East Midlands": ["nottingham", "leicester", "derby", "lincoln", "northampton"],
    "East of England": ["cambridge", "norwich", "ipswich", "peterborough", "luton", "essex", "norfolk", "suffolk"],
    "London": ["london", "westminster", "camden", "hackney", "islington", "greenwich", "southwark", "croydon", "lambeth", "tfl"],
    "South East": ["southampton", "brighton", "reading", "oxford", "milton keynes", "portsmouth", "kent", "surrey", "sussex"],
    "South West": ["bristol", "plymouth", "exeter", "bath", "gloucester", "cornwall", "devon", "somerset"],
    "Wales": ["cardiff", "swansea", "newport", "wrexham", "welsh"],
    "Scotland": ["glasgow", "edinburgh", "aberdeen", "dundee", "scottish"],
    "Northern Ireland": ["belfast", "derry", "londonderry"],
}

# Keywords -> TOM theme names as used in the TOM Measures table.
THEME_KEYWORDS = {
    "Work": ["employment", "jobs", "job ", "apprentic", "youth", "neet", "skills", "recruit", "career", "training", "unemploy", "work placement"],
    "Economy": ["supply chain", "sme", "vcse", "local spend", "local business", "procurement", "subcontract", "economic"],
    "Community": ["community", "digital inclusion", "wellbeing", "well-being", "health", "volunteer", "school", "education", "charity", "inclusion"],
    "Planet": ["net zero", "carbon", "climate", "environment", "green", "emission", "sustainab", "decarbon"],
}

_AUTHORITY = re.compile(
    r"\b((?:[A-Z][\w'&-]*\s+){0,4}(?:City Council|County Council|Borough Council|Council|Combined Authority|"
    r"NHS Foundation Trust|NHS Trust|Teaching Hospitals|Health Board|Police|University|Government|Authority))\b"
)
_MONEY = re.compile(r"(?:£|gbp\s*)\s*([\d,]+(?:\.\d+)?)\s*(bn|billion|m|mn|million|k|thousand)?\b|\b([\d,]+(?:\.\d+)?)\s*(bn|billion|m|mn|million|k|thousand)\b", re.IGNORECASE)
_MULT = {"bn": 1e9, "billion": 1e9, "m": 1e6, "mn": 1e6, "million": 1e6, "k": 1e3, "thousand": 1e3}


def _money(text: str) -> Optional[float]:
    m = _MONEY.search(text)
    if not m:
        return None
    number, unit = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
    value = float(number.replace(",", ""))
    if unit:
        value *= _MULT[unit.lower()]
    elif value < 1000:  # "£10" in a tender brief means £10M
        value *= 1e6
    return value


def _region(text: str, regions: List[str]) -> Optional[str]:
    lower = text.lower()
    for region in sorted(regions, key=len, reverse=True):  # "North East" before "East"
        if re.search(r"\b" + re.escape(region.lower()) + r"\b", lower):
            return region
    for region, places in CITY_REGION.items():
        if region in regions and any(re.search(r"\b" + re.escape(p), lower) for p in places):
            return region
    return None


def parse_tender_prompt(text: str, tables: dict) -> Dict[str, Any]:
    regions = [r["region"] for r in tables["regions"]]
    table_themes = list(dict.fromkeys(m["theme"] for m in tables["measures"] if m.get("theme")))
    lower = text.lower()

    form: Dict[str, Any] = {}
    if (value := _money(text)) is not None:
        form["bid_amount_gbp"] = value
    if m := re.search(r"(\d+(?:\.\d+)?)\s*(?:%|per\s?cent)", text, re.IGNORECASE):
        form["sv_percent"] = float(m.group(1))
    if m := re.search(r"(\d+(?:\.\d+)?)\s*[- ]?(?:years?|yrs?)\b", text, re.IGNORECASE):
        form["duration_years"] = float(m.group(1))
    elif m := re.search(r"(\d+)\s*[- ]?months?\b", text, re.IGNORECASE):
        form["duration_years"] = round(int(m.group(1)) / 12, 1)
    if region := _region(text, regions):
        form["region"] = region
    themes = [t for t in table_themes if any(k in lower for k in THEME_KEYWORDS.get(t, []))]
    if themes:
        form["themes"] = themes
    if m := _AUTHORITY.search(text):
        form["client"] = m.group(1).strip()

    expected = ["bid_amount_gbp", "sv_percent", "duration_years", "region", "themes", "client"]
    return {
        "form": form,
        "found": [k for k in expected if k in form],
        "missing": [k for k in expected if k not in form],
    }
