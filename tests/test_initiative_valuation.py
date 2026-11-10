"""Rules and valuation for the Initiative Generator (no AI, no database).

Expected numbers come from the Monk Spaces workbook (TOM Measures, Localisation, Assumptions).
"""
import pytest

from app.knowledge import load_tables
from app.services.initiative_valuation import (
    ALTERNATIVE,
    CONDITIONAL,
    COUNTED,
    NOT_VALUED,
    TenderForm,
    localised_proxy,
    value_initiatives,
)

TABLES = load_tables()
COMPUTING = "Computer programming, consultancy and related services"


def form(**kw):
    base = dict(company="Infosys", bid_amount_gbp=10_000_000, sv_percent=10, region="North East", duration_years=3, industry=COMPUTING)
    base.update(kw)
    return TenderForm(**base)


def run(*initiatives, **form_kw):
    return value_initiatives({"initiatives": list(initiatives)}, TABLES, form(**form_kw))


def line(result, i=0, j=0):
    return result["initiatives"][i]["lines"][j]


# ── Localised proxies reproduce the workbook (A-03) ──────────────────────────
def test_nt1_is_regional_median_wage():
    assert localised_proxy("NT1", TABLES, "North East", COMPUTING)[0] == pytest.approx(37666.5)


def test_nt18_and_nt19_match_workbook_values():
    assert localised_proxy("NT18", TABLES, "North East", COMPUTING)[0] == pytest.approx(0.990909603164808)
    assert localised_proxy("NT19", TABLES, "North East", COMPUTING)[0] == pytest.approx(0.998143243267912)


def test_unlocalised_measure_uses_national_proxy():
    assert localised_proxy("NT8", TABLES, "London", COMPUTING)[0] == pytest.approx(17.48)


def test_region_changes_nt1_value():
    ne = localised_proxy("NT1", TABLES, "North East", COMPUTING)[0]
    london = localised_proxy("NT1", TABLES, "London", COMPUTING)[0]
    assert london != ne


# ── Code does the maths: units × proxy ───────────────────────────────────────
def test_value_is_units_times_proxy():
    r = run({"name": "Code clubs", "lines": [{"measure": "NT8", "units": 600}]})
    assert line(r)["value_gbp"] == pytest.approx(600 * 17.48)
    assert r["totals"]["infosys_gbp"] == pytest.approx(10_488.0)


def test_cost_is_always_blank_and_every_initiative_is_a_proposal():
    r = run({"name": "Code clubs", "lines": [{"measure": "NT8", "units": 10}]})
    ini = r["initiatives"][0]
    assert ini["cost_gbp"] is None
    assert ini["status"] == "Proposal"
    assert any("Confirm cost" in q for q in ini["questions"])


# ── Rule 2: no £ values from the AI ──────────────────────────────────────────
def test_ai_money_fields_are_ignored():
    r = run({"name": "X", "value_gbp": 999999, "lines": [{"measure": "NT8", "units": 10, "value": 5_000_000, "proxy": 1000}]})
    assert line(r)["value_gbp"] == pytest.approx(174.8)
    assert any("ignored" in c for c in r["checks"])


def test_money_in_bid_paragraph_is_masked():
    r = run({"name": "X", "bid_paragraph": "This delivers £1.2m of value.", "lines": [{"measure": "NT8", "units": 1}]})
    assert "£" not in r["initiatives"][0]["bid_paragraph"]


# ── Unknown measures and bad quantities are not valued ───────────────────────
def test_unknown_measure_not_valued():
    r = run({"name": "X", "lines": [{"measure": "NT20", "units": 100}]})
    assert line(r)["status"] == NOT_VALUED and line(r)["value_gbp"] == 0


def test_missing_units_not_valued():
    r = run({"name": "X", "lines": [{"measure": "NT8", "units": "lots"}]})
    assert line(r)["status"] == NOT_VALUED


# ── A-07: no double counting of the same people ──────────────────────────────
def test_apprentices_nt10_and_nt4_not_added_twice():
    r = run({"name": "Ambassadors", "lines": [{"measure": "NT10", "units": 520}, {"measure": "NT4", "units": 10, "people": 10}]})
    assert line(r, 0, 0)["status"] == COUNTED
    assert line(r, 0, 1)["status"] == ALTERNATIVE
    assert r["totals"]["infosys_gbp"] == pytest.approx(520 * 309.73)


# ── A-06 / NT1: FTE caps per person ──────────────────────────────────────────
def test_barrier_measure_capped_at_one_fte_year_per_person():
    r = run({"name": "NEET hires", "lines": [{"measure": "NT4", "units": 9, "people": 3}]})
    assert line(r)["units"] == 3


def test_nt1_capped_at_people_times_years():
    r = run({"name": "Local hires", "lines": [{"measure": "NT1", "units": 50, "people": 4}]}, duration_years=3)
    assert line(r)["units"] == 12


# ── A-13: carbon is conditional, outside the core total ──────────────────────
def test_carbon_is_conditional():
    r = run({"name": "Green cloud", "lines": [{"measure": "NT31", "units": 100}]})
    assert line(r)["status"] == CONDITIONAL
    assert r["totals"]["infosys_gbp"] == 0
    assert r["totals"]["conditional_gbp"] == pytest.approx(100 * 252.11)


# ── A-09: partner-led value reported separately ──────────────────────────────
def test_partner_value_is_separate():
    r = run(
        {"name": "Ours", "lines": [{"measure": "NT8", "units": 100}]},
        {"name": "Theirs", "attribution": "Partner-led", "lines": [{"measure": "NT8", "units": 50}]},
    )
    assert r["totals"]["infosys_gbp"] == pytest.approx(1748.0)
    assert r["totals"]["partner_gbp"] == pytest.approx(874.0)


# ── Realistic scale ──────────────────────────────────────────────────────────
def test_spend_cannot_exceed_contract_value():
    r = run({"name": "SME spend", "lines": [{"measure": "NT19", "units": 50_000_000}]}, bid_amount_gbp=1_000_000)
    assert line(r)["units"] == 1_000_000


def test_far_above_target_is_flagged():
    r = run({"name": "Hires", "lines": [{"measure": "NT1", "units": 100, "people": 40}]}, bid_amount_gbp=1_000_000)
    assert any("check the units are realistic" in c for c in r["checks"])
