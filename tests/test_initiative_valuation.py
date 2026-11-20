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
        # A different measure: the same one in two initiatives is claimed once.
        {"name": "Theirs", "attribution": "Partner-led", "lines": [{"measure": "NT17", "units": 50}]},
    )
    assert r["totals"]["infosys_gbp"] == pytest.approx(1748.0)
    assert r["totals"]["partner_gbp"] == pytest.approx(50 * localised_proxy("NT17", TABLES, "North East", COMPUTING)[0])


def test_same_measure_across_the_package_is_counted_once():
    r = run(
        {"name": "Ours", "lines": [{"measure": "NT8", "units": 100}]},
        {"name": "Theirs", "attribution": "Partner-led", "lines": [{"measure": "NT8", "units": 50}]},
    )
    assert line(r, 1)["status"] == ALTERNATIVE
    assert not any("not added" in c for c in r["checks"])  # the line says why; the audit keeps the record
    assert any(a["action"] == "not added" for a in r["sizing"]["adjustments"])


# ── Realistic scale ──────────────────────────────────────────────────────────
def test_spend_cannot_exceed_contract_value():
    # Target is high enough that only the contract-value cap applies.
    r = run({"name": "SME spend", "lines": [{"measure": "NT19", "units": 50_000_000}]}, bid_amount_gbp=1_000_000, sv_percent=100)
    assert line(r)["units"] == 1_000_000


def test_far_above_target_is_recorded_for_audit_not_shown():
    r = run({"name": "Hires", "lines": [{"measure": "NT1", "units": 100, "people": 40}]}, bid_amount_gbp=1_000_000)
    assert not any("realistic" in c or "brought down" in c.lower() for c in r["checks"])
    assert any(a["action"] == "far above target" for a in r["sizing"]["adjustments"])


# ── Parts: the AI gives people × rate × years, the code multiplies ───────────
def apprentices(people=12, per=46, years=3, **extra):
    return {"name": "Apprentices", "bid_paragraph": f"We will employ {people} apprentices.",
            "lines": [{"measure": "NT10", "people": people, "who": "apprentices",
                       "per_person_per_year": per, "years": years, **extra}]}


def test_units_are_the_product_of_the_parts():
    r = run(apprentices(units=99_999))  # a stray AI total is ignored
    ln = line(r)
    assert ln["units"] == 12 * 46 * 3
    assert ln["basis"] == "12 apprentices × 46 weeks a year × 3 years"
    assert ln["value_gbp"] == pytest.approx(ln["units"] * ln["proxy_gbp"])


def test_parts_are_held_to_what_a_person_and_the_contract_can_give():
    r = run(apprentices(per=80, years=9), duration_years=3)
    assert line(r)["units"] == 12 * 52 * 3
    assert not line(r)["note"]  # corrected quietly; recorded for audit
    assert len([a for a in r["sizing"]["adjustments"] if a["action"] == "corrected"]) == 2


def test_weeks_given_as_a_share_of_the_year_are_read_as_weeks():
    r = run(apprentices(per=0.88), sv_percent=100)
    assert line(r)["units"] == 12 * 46 * 3


def test_weeks_without_parts_are_capped_per_person():
    r = run({"name": "Apprentices", "lines": [{"measure": "NT10", "units": 23040, "people": 80,
                                              "basis": "80 apprentices x 24 months x 48 weeks per year"}]},
            duration_years=5, sv_percent=100)
    assert line(r)["units"] == 80 * 52 * 5
    assert line(r)["basis"] == ""  # the AI's arithmetic no longer describes the number


# ── Sizing to target: whole people, just under the target, quietly ───────────
def test_package_above_target_is_sized_in_whole_people_just_under_target():
    r = run(apprentices(people=40, per=46, years=3), bid_amount_gbp=1_000_000, sv_percent=20)  # target £200,000
    ln = line(r)
    assert float(ln["people"]).is_integer() and ln["people"] < 40
    assert ln["units"] == ln["people"] * 46 * 3
    assert ln["basis"].startswith(f"{ln['people']:g} apprentices")
    assert ln["people"] > 1
    assert r["totals"]["infosys_gbp"] <= 200_000
    assert r["totals"]["infosys_gbp"] > 200_000 - 46 * 3 * ln["proxy_gbp"]  # within one person of it
    assert f"employ {ln['people']:g} apprentices" in r["initiatives"][0]["bid_paragraph"]
    assert not any("brought down" in c.lower() for c in r["checks"]) and not ln["note"]
    assert any(a["action"] == "sized to target" for a in r["sizing"]["adjustments"])


def test_package_under_target_is_left_alone():
    r = run(apprentices(people=2, per=46, years=3))
    assert line(r)["people"] == 2 and r["sizing"]["adjustments"] == []


def test_spend_is_sized_in_round_steps():
    r = run({"name": "SME spend", "lines": [{"measure": "NT19", "units": 900_000}]}, bid_amount_gbp=1_000_000, sv_percent=10)
    units = line(r)["units"]
    assert units % 1000 == 0 and r["totals"]["infosys_gbp"] <= 100_000


def test_package_far_above_target_drops_whole_lines_largest_first():
    r = run(apprentices(people=40, per=46, years=3),
            {"name": "Volunteering", "lines": [{"measure": "NT8", "units": 50}]},
            bid_amount_gbp=1_000_000, sv_percent=10)  # target £100,000
    assert line(r, 0)["people"] < 40  # the largest line is cut first, in whole people
    assert line(r, 1)["units"] == 50 and line(r, 1)["status"] == COUNTED  # the small one is untouched
    assert r["totals"]["infosys_gbp"] <= 100_000
    assert not any("cut back" in c or "proposed" in c for c in r["checks"])


def test_far_above_target_keeps_every_line_and_cuts_from_the_top():
    r = run(apprentices(people=40, per=46, years=3),
            {"name": "SME spend", "lines": [{"measure": "NT19", "units": 2_000_000, "basis": "Spend with local SMEs"}]},
            {"name": "Volunteering", "lines": [{"measure": "NT8", "units": 50}]},
            bid_amount_gbp=3_000_000, sv_percent=10)  # target £300,000, about twenty times over
    assert all(line(r, i)["status"] == COUNTED for i in range(3))  # no jobs or spend lost to meet a number
    assert line(r, 2)["units"] == 50  # the small line is untouched
    assert line(r, 1)["basis"] == "Spend with local SMEs"  # wording without arithmetic is kept
    assert 290_000 < r["totals"]["infosys_gbp"] <= 300_000


def test_a_line_too_big_for_the_target_becomes_an_alternative():
    r = run(apprentices(people=40, per=46, years=3),
            {"name": "Volunteering", "lines": [{"measure": "NT8", "units": 50}]},
            bid_amount_gbp=1_000_000, sv_percent=1)  # target £10,000: one apprentice is worth more
    assert line(r, 0)["status"] == ALTERNATIVE and line(r, 0)["people"] == 40  # kept as proposed, not added
    assert line(r, 1)["status"] == COUNTED
    assert r["totals"]["infosys_gbp"] <= 10_000
    assert not any("cut back" in c or "proposed" in c for c in r["checks"])


# --- Quantity checks: the AI does its own arithmetic for units; the code flags sums that do not add up.

from app.services.initiative_valuation import _MONEY_TEXT, quantity_doubts


def test_money_removed_from_paragraph_keeps_the_spacing():
    assert _MONEY_TEXT.sub("[value]", "at least £1,200,000 in local spend") == "at least [value] in local spend"
    assert _MONEY_TEXT.sub("[value]", "costs £500.") == "costs [value]."
    assert _MONEY_TEXT.sub("[value]", "worth £1.2m, and") == "worth [value], and"


def test_units_that_do_not_match_their_basis_are_flagged():
    doubts = quantity_doubts(23040, "80 apprentices x 24 months x 48 weeks per year (average)", "no. weeks", 5)
    assert "92,160" in doubts[0]  # 80 x 24 x 48
    assert "288 weeks per person" in doubts[1]  # more than 52 x 5 = 260


def test_sound_units_are_not_flagged():
    assert quantity_doubts(1000, "250 young people x 4 weeks virtual work experience each", "no. weeks", 5) == []
    assert quantity_doubts(360, "120 workshops x 3 hours x 1 expert per session", "no. hours", 5) == []
    assert quantity_doubts(10, "10 long-term unemployed recruited for 1 FTE year each", "no. people FTE", 5) == []
    assert quantity_doubts(5000, "Training totalling 5,000 weeks", "no. weeks", 5) == []


def test_a_doubtful_quantity_is_recorded_for_audit_not_shown():
    bad = {"name": "Apprentices", "lines": [{"measure": "NT10", "units": 23040,
                                            "basis": "80 apprentices x 24 months x 48 weeks per year"}]}
    r = run(bad, duration_years=5, sv_percent=100)
    ln = line(r)
    assert ln["status"] == COUNTED and ln["units"] == 23040
    assert not ln["note"] and not any("quantity" in c.lower() for c in r["checks"])
    assert any(a["action"] == "doubt" and "92,160" in a["reason"] for a in r["sizing"]["adjustments"])
