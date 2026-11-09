import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.calculation_service import calculation_service, DEFAULT_TOMS_DATA, MASTER_INITIATIVES_DATA
from app.services.rag_service import (
    rag_service,
    INDICATIVE_UNIT_DELIVERY_COSTS,
    APPROVED_PARTNER_ECOSYSTEM,
    _volume_consistency_issue,
)
from app.services.prompt_interpreter_service import _safe_number
from app.schemas.response import OpportunityRequest, InitiativeItem


# Official Open Access TOM System 2024/2025 proxy values held in the catalog.
NT8_STAFF_HOUR = 17.48
NT10_APPRENTICE_WEEK = 309.73
NT4_NEET_FTE = 53013.0


def test_toms_metrics_catalog():
    metrics = calculation_service.get_all_metrics()
    codes = [m.code for m in metrics]
    for code in ["NT1", "NT3", "NT4", "NT8", "NT10", "NT14", "NT18", "NT19", "NT27", "NT31"]:
        assert code in codes
    # NT20 is not a measure in the Open Access TOM System catalog.
    assert "NT20" not in codes


def test_deterministic_initiative_calculation():
    # NT8 = £17.48 per staff volunteering hour. 72 hrs/yr × 3 yrs = 216 hrs = £3,775.68
    calc = calculation_service.calculate_initiative(
        initiative_name="School careers volunteering",
        toms_code="NT8",
        annual_volume=72.0,
        duration_years=3
    )
    assert calc.toms_code == "NT8"
    assert calc.total_volume == 216.0
    assert calc.unit_value_gbp == NT8_STAFF_HOUR
    assert calc.total_social_value_gbp == 3775.68


def test_unknown_code_is_valued_at_zero():
    calc = calculation_service.calculate_initiative("Device bank", "NT20", 60.0, 3)
    assert calc.total_social_value_gbp == 0.0
    assert calc.metric_name == "Unmapped Custom Initiative"


def test_deterministic_package_calculation():
    initiatives = [
        {"name": "Apprentices", "toms_metric_code": "NT10", "annual_volume": 104.0},
        {"name": "NEET recruitment", "toms_metric_code": "NT4", "annual_volume": 2.0},
    ]
    # NT10: 104 × 3 × 309.73 = 96,635.76 ; NT4: 2 × 3 × 53,013 = 318,078 ; total = 414,713.76
    pkg = calculation_service.calculate_package(
        package_name="Test Core Package",
        initiatives=initiatives,
        contract_value_gbp=10000000.0,
        duration_years=3,
        target_weighting_percent=10.0
    )
    assert pkg.total_social_value_gbp == 414713.76
    assert pkg.target_social_value_gbp == 1000000.00
    assert pkg.social_value_percentage == 4.15
    assert pkg.target_met is False
    assert len(pkg.audit_trail) == 3


def test_master_initiatives_load_without_confidential_fields():
    assert len(MASTER_INITIATIVES_DATA) == 37
    for item in MASTER_INITIATIVES_DATA:
        assert "defensible_value_gbp" not in item
        assert "valuation_status" not in item
    filtered = calculation_service.get_master_initiatives(pillar="SV1")
    assert filtered and all("sv1" in x["pillar"].lower() for x in filtered)


def test_cost_and_partner_tables_only_use_catalog_codes():
    catalog_codes = {item["code"] for item in DEFAULT_TOMS_DATA}
    assert set(INDICATIVE_UNIT_DELIVERY_COSTS) <= catalog_codes
    for city, partners in APPROVED_PARTNER_ECOSYSTEM.items():
        code_keys = {k for k in partners if k.startswith("NT")}
        assert code_keys <= catalog_codes, city


def _request() -> OpportunityRequest:
    return OpportunityRequest(
        contract_duration_years=3,
        contract_value_gbp=10000000.0,
        social_value_weighting_percent=10.0,
        client="Birmingham City Council",
        location="Birmingham",
        priorities=["Youth Employment"],
    )


def test_package_build_ignores_llm_costs_and_handles_nulls():
    pkg_data = {
        "initiatives": [
            {
                "name": "Apprenticeships",
                "theme": "Employment & Skills",
                "toms_metric_code": "nt10",
                "annual_volume": "52",
                "indicative_cost_gbp": 999999.0,  # must be ignored
                "sessions_per_year": None,
            },
            {"name": "Broken item", "toms_metric_code": None, "annual_volume": None},
        ]
    }
    pkg = rag_service._build_social_value_package(pkg_data, "Core Package", _request(), [], "")
    apprentices, broken = pkg.initiatives
    assert apprentices.toms_metric_code == "NT10"
    assert apprentices.indicative_cost_gbp == round(52 * 3 * INDICATIVE_UNIT_DELIVERY_COSTS["NT10"], 2)
    assert broken.annual_volume == 0.0
    assert pkg.financial_calculation.total_social_value_gbp == round(52 * 3 * NT10_APPRENTICE_WEEK, 2)


def test_volume_consistency_for_staff_hours():
    metric = calculation_service.get_metric_by_code(None, "NT8")
    base = dict(theme="Work", location="X", description="d", delivery_mechanism="m",
                target_beneficiaries="b", evidence_source="Model recommended", toms_metric_code="NT8",
                sessions_per_year=12, hours_per_session=3)
    ok = InitiativeItem(name="A", annual_volume=72, **base)
    too_low = InitiativeItem(name="B", annual_volume=10, **base)
    assert _volume_consistency_issue(ok, metric) is None
    assert "differs" in _volume_consistency_issue(too_low, metric)


@pytest.mark.parametrize("raw,expected", [(None, 3.0), ("", 3.0), ("£10,000,000", 10000000.0), ("12%", 12.0), ("abc", 3.0), (5, 5.0)])
def test_safe_number(raw, expected):
    assert _safe_number(raw, 3.0) == expected
