"""
Import the Monk Spaces knowledge-base workbook into app/knowledge/tables.json.

The workbook is the single source of facts (scope §4): TOM measures and proxies,
localisation factors, settings, the initiative library and, when Saloni adds them,
the Patterns / Measure-MAC / Capability / Wording sheets. The generator only ever
reads values from tables.json, never from AI output.

Yearly update (scope §5): drop the new edition into the workbook, run

    python scripts/import_workbook.py "../docs/<workbook>.xlsx"

review the diff of app/knowledge/tables.json, and commit it.
"""
import json
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

import openpyxl

OUT = Path(__file__).resolve().parent.parent / "app" / "knowledge" / "tables.json"

# Optional sheets Saloni maintains; imported generically (header row -> list of dicts) when present.
OPTIONAL_SHEETS = {"Patterns": "patterns", "Measure-MAC": "measure_mac", "Capability": "capability", "Wording": "wording"}


def _rows(ws):
    return [list(r) for r in ws.iter_rows(values_only=True)]


def _table(ws, first_header: str):
    """Rows under the header row whose first cell is `first_header`, as dicts (stops at the first empty row)."""
    rows = _rows(ws)
    for i, row in enumerate(rows):
        if row and row[0] == first_header:
            header = [str(h).strip() if h is not None else "" for h in row]
            out = []
            for r in rows[i + 1:]:
                if not r or all(c is None for c in r):
                    break
                out.append({header[j]: r[j] for j in range(len(header)) if header[j]})
            return out
    raise ValueError(f"Sheet '{ws.title}': header row starting with '{first_header}' not found")


def _num(v):
    return float(v) if isinstance(v, (int, float)) else None


def _setting(settings_rows, prefix: str):
    for r in settings_rows:
        if str(r.get("Setting", "")).startswith(prefix):
            return r.get("Value")
    raise ValueError(f"Settings: no row starting with '{prefix}'")


def import_workbook(path: Path) -> dict:
    warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)

    measures = []
    for m in _table(wb["TOM Measures"], "Theme"):
        if not m.get("Ref"):
            continue
        measures.append({
            "code": str(m["Ref"]).strip(),
            "theme": m.get("Theme"),
            "outcome": m.get("Outcome"),
            "name": m.get("Measure"),
            "unit": m.get("Unit"),
            "proxy_gbp": _num(m.get("Proxy £ per unit")),
            "localised": str(m.get("Localised?", "")).strip().lower() == "yes",
            "unit_guidance": (str(m.get("Unit guidance") or "").split("\n")[0])[:240],
        })

    regions, industries = [], []
    for r in _table(wb["Localisation"], "Region"):
        if r.get("Region") and _num(r.get("Median annual wage (£)")) is not None:
            regions.append({
                "region": r["Region"],
                "median_wage_gbp": _num(r["Median annual wage (£)"]),
                "regional_gva": _num(r.get("Regional GVA factor")),
            })
        if r.get("Industry") and _num(r.get("GVA multiplier")) is not None:
            industries.append({"industry": str(r["Industry"]).strip(), "gva_multiplier": _num(r["GVA multiplier"])})

    settings_rows = _table(wb["Settings"], "Setting")
    settings = {
        "default_region": _setting(settings_rows, "Region"),
        "default_industry": str(_setting(settings_rows, "Industry")).strip(),
        "carbon_baseline_rate": _num(_setting(settings_rows, "Net zero annual reduction baseline")),
        "nt19_factor": 1.0073,  # Assumptions A-03: NT19 = NT18 × 1.0073
    }

    valuation = _table(wb["Valuation"], "Line")
    measures_by_initiative: dict = {}
    for v in valuation:
        if v.get("Initiative ID") and v.get("Measure code"):
            measures_by_initiative.setdefault(v["Initiative ID"], set()).add(str(v["Measure code"]).strip())
    library = []
    for i in _table(wb["Initiatives"], "ID"):
        library.append({
            "id": i["ID"],
            "pillar": i.get("Pillar"),
            "mac": i.get("MAC"),
            "name": i.get("Initiative"),
            "what": i.get("What is committed"),
            "delivered_by": i.get("Delivered by"),
            "attribution": i.get("Attribution"),
            "measures": sorted(measures_by_initiative.get(i["ID"], [])),
        })

    tables = {
        "source": path.name,
        "edition": "Open Access TOM System Edition 2025",
        "imported_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "settings": settings,
        "measures": measures,
        "regions": regions,
        "industries": industries,
        "initiative_library": library,
    }
    for sheet, key in OPTIONAL_SHEETS.items():
        tables[key] = _table(wb[sheet], _rows(wb[sheet])[3][0]) if sheet in wb.sheetnames else []
    return tables


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    tables = import_workbook(Path(sys.argv[1]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(tables, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(
        f"Wrote {OUT.relative_to(OUT.parent.parent.parent)}: {len(tables['measures'])} measures, "
        f"{len(tables['regions'])} regions, {len(tables['industries'])} industries, "
        f"{len(tables['initiative_library'])} library initiatives, patterns={len(tables['patterns'])}, "
        f"measure-MAC={len(tables['measure_mac'])}, capability={len(tables['capability'])}"
    )


if __name__ == "__main__":
    main()
