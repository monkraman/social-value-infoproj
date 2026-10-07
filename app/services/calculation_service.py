from typing import List, Dict, Optional, Any
from app.schemas.calculation import TOMsMetric, InitiativeCalculation, PackageCalculation

# Synthetic National TOMs proxy metrics catalog (clearly labeled as synthetic POC values)
SYNTHETIC_TOMS_CATALOG: Dict[str, Dict[str, Any]] = {
    "NT1": {
        "code": "NT1",
        "name": "Local Apprenticeship Weeks",
        "theme": "Employment & Skills",
        "unit": "weeks",
        "unit_value_gbp": 215.00,
        "description": "Number of weeks of local apprentice training delivered during the contract period.",
        "is_synthetic": True
    },
    "NT3": {
        "code": "NT3",
        "name": "Young People Supported into Employment (16-24 NEET)",
        "theme": "Youth Employment",
        "unit": "people",
        "unit_value_gbp": 4850.00,
        "description": "Young people (NEET) supported with career coaching, internships, and sustained entry into work.",
        "is_synthetic": True
    },
    "NT8": {
        "code": "NT8",
        "name": "Digital Inclusion / Skills Workshops",
        "theme": "Digital Inclusion",
        "unit": "workshops",
        "unit_value_gbp": 1250.00,
        "description": "Community-based digital literacy, online safety, and accessibility training workshops.",
        "is_synthetic": True
    },
    "NT10": {
        "code": "NT10",
        "name": "Staff Digital & STEM Volunteering Hours",
        "theme": "Community Engagement",
        "unit": "hours",
        "unit_value_gbp": 45.00,
        "description": "Dedicated employee volunteer hours supporting local schools, colleges, and charities.",
        "is_synthetic": True
    },
    "NT14": {
        "code": "NT14",
        "name": "Local SME & VCSE Supply Chain Spend Proxy",
        "theme": "Economic Growth",
        "unit": "GBP spend",
        "unit_value_gbp": 0.22,
        "description": "Direct supply chain spend awarded to local small businesses and voluntary sector partners.",
        "is_synthetic": True
    },
    "NT20": {
        "code": "NT20",
        "name": "Refurbished Digital Devices Donated",
        "theme": "Digital Inclusion",
        "unit": "devices",
        "unit_value_gbp": 320.00,
        "description": "Laptops and tablets wiped, refurbished, and donated with connectivity to disadvantaged residents.",
        "is_synthetic": True
    }
}


class CalculationService:
    """
    Deterministic Social Value Calculation Layer.
    Ensures all calculations are auditable and strictly separated from LLM generation.
    """

    def __init__(self, catalog: Optional[Dict[str, Dict[str, Any]]] = None):
        self.catalog = catalog or SYNTHETIC_TOMS_CATALOG

    def get_all_metrics(self) -> List[TOMsMetric]:
        """Returns all available proxy TOMs metrics."""
        return [TOMsMetric(**data) for data in self.catalog.values()]

    def get_metric(self, code: Optional[str]) -> Optional[TOMsMetric]:
        """Finds a metric by code (case-insensitive)."""
        if not code:
            return None
        code_upper = code.strip().upper()
        if code_upper in self.catalog:
            return TOMsMetric(**self.catalog[code_upper])
        return None

    def calculate_initiative(
        self,
        initiative_name: str,
        toms_code: Optional[str],
        annual_volume: float,
        duration_years: int
    ) -> InitiativeCalculation:
        """
        Deterministically calculates the social value for an individual initiative.
        Formula: Annual Volume × Contract Duration (Years) × Unit Value (GBP)
        """
        metric = self.get_metric(toms_code)

        if metric:
            unit_val = metric.unit_value_gbp
            unit_name = metric.unit
            metric_title = metric.name
            code = metric.code
        else:
            # Fallback if no specific TOMs code matched
            unit_val = 0.0
            unit_name = "units"
            metric_title = "Unmapped Social Value Metric"
            code = "UNMAPPED"

        total_volume = round(annual_volume * duration_years, 2)
        total_sv = round(total_volume * unit_val, 2)
        formula = (
            f"{annual_volume:,.1f} {unit_name}/yr × {duration_years} yrs = "
            f"{total_volume:,.1f} {unit_name} @ £{unit_val:,.2f} = £{total_sv:,.2f}"
        )

        return InitiativeCalculation(
            initiative_name=initiative_name,
            toms_code=code,
            metric_name=metric_title,
            unit=unit_name,
            unit_value_gbp=unit_val,
            annual_volume=annual_volume,
            duration_years=duration_years,
            total_volume=total_volume,
            total_social_value_gbp=total_sv,
            calculation_formula=formula
        )

    def calculate_package(
        self,
        package_name: str,
        initiatives: List[Dict[str, Any]],
        contract_value_gbp: float,
        duration_years: int,
        target_weighting_percent: float
    ) -> PackageCalculation:
        """
        Aggregates individual initiative calculations into an auditable package total.
        """
        calc_initiatives: List[InitiativeCalculation] = []
        total_sv = 0.0
        audit_trail: List[str] = []

        for item in initiatives:
            name = item.get("name", "Unnamed Initiative")
            code = item.get("toms_metric_code")
            vol = float(item.get("annual_volume", 1.0))

            init_calc = self.calculate_initiative(
                initiative_name=name,
                toms_code=code,
                annual_volume=vol,
                duration_years=duration_years
            )
            calc_initiatives.append(init_calc)
            total_sv += init_calc.total_social_value_gbp
            audit_trail.append(f"[{init_calc.toms_code}] {name}: {init_calc.calculation_formula}")

        total_sv = round(total_sv, 2)
        sv_percent = round((total_sv / contract_value_gbp * 100.0) if contract_value_gbp > 0 else 0.0, 2)
        target_sv = round((contract_value_gbp * (target_weighting_percent / 100.0)), 2)
        target_met = total_sv >= target_sv

        audit_trail.append(
            f"Package Total: £{total_sv:,.2f} ({sv_percent}% of £{contract_value_gbp:,.2f} contract value). "
            f"Target ({target_weighting_percent}%): £{target_sv:,.2f} -> {'MET' if target_met else 'GAP'}"
        )

        return PackageCalculation(
            package_name=package_name,
            initiatives=calc_initiatives,
            total_social_value_gbp=total_sv,
            contract_value_gbp=contract_value_gbp,
            social_value_percentage=sv_percent,
            target_weighting_percent=target_weighting_percent,
            target_social_value_gbp=target_sv,
            target_met=target_met,
            audit_trail=audit_trail
        )


calculation_service = CalculationService()
