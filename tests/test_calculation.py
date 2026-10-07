import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.calculation_service import calculation_service


def test_toms_metrics_catalog():
    metrics = calculation_service.get_all_metrics()
    assert len(metrics) >= 6
    codes = [m.code for m in metrics]
    assert "NT1" in codes
    assert "NT3" in codes
    assert "NT8" in codes
    assert "NT10" in codes
    assert "NT14" in codes
    assert "NT20" in codes


def test_deterministic_initiative_calculation():
    # NT8 = £1250 / workshop. 4 workshops/yr * 3 yrs = 12 workshops * £1250 = £15,000.00
    calc = calculation_service.calculate_initiative(
        initiative_name="Digital Inclusion Workshop",
        toms_code="NT8",
        annual_volume=4.0,
        duration_years=3
    )
    assert calc.toms_code == "NT8"
    assert calc.total_volume == 12.0
    assert calc.unit_value_gbp == 1250.00
    assert calc.total_social_value_gbp == 15000.00
    assert "4.0 workshops/yr × 3 yrs = 12.0 workshops @ £1,250.00 = £15,000.00" in calc.calculation_formula


def test_deterministic_package_calculation():
    initiatives = [
        {"name": "Digital Inclusion", "toms_metric_code": "NT8", "annual_volume": 4.0},
        {"name": "Youth Pathways", "toms_metric_code": "NT3", "annual_volume": 3.0}
    ]
    # NT8: 4 * 3 * 1250 = £15,000
    # NT3: 3 * 3 * 4850 = £43,650
    # Total = £58,650
    pkg = calculation_service.calculate_package(
        package_name="Test Core Package",
        initiatives=initiatives,
        contract_value_gbp=10000000.0,
        duration_years=3,
        target_weighting_percent=10.0
    )
    assert pkg.total_social_value_gbp == 58650.00
    assert pkg.target_social_value_gbp == 1000000.00
    assert pkg.social_value_percentage == 0.59
    assert pkg.target_met is False
    assert len(pkg.audit_trail) == 3
