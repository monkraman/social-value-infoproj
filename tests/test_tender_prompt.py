"""Reading a plain-English tender description into the Initiative Generator form (no AI)."""
import pytest

from app.knowledge import load_tables
from app.services.tender_prompt import parse_tender_prompt

TABLES = load_tables()
REGIONS = {r["region"] for r in TABLES["regions"]}

BIRMINGHAM = (
    "I need to build a Social Value bid response, for a 3-year contract of £10M with 10% Social Value weighting. "
    "The client Birmingham City Council in Birmingham wants the Social Value offer to address digital inclusion "
    "and youth employment."
)


def parse(text):
    return parse_tender_prompt(text, TABLES)


def test_full_brief_fills_every_field():
    r = parse(BIRMINGHAM)
    f = r["form"]
    assert f["bid_amount_gbp"] == 10_000_000
    assert f["sv_percent"] == 10
    assert f["duration_years"] == 3
    assert f["region"] == "West Midlands"
    assert set(f["themes"]) == {"Work", "Community"}
    assert f["client"] == "Birmingham City Council"
    assert r["missing"] == []


@pytest.mark.parametrize(
    "text,region",
    [
        ("NHS trust in Leeds", "Yorkshire and The Humber"),
        ("Manchester City Council", "North West"),
        ("a contract in the North East", "North East"),
        ("Glasgow", "Scotland"),
        ("Camden council", "London"),
        ("Cardiff", "Wales"),
    ],
)
def test_city_maps_to_table_region(text, region):
    assert parse(text)["form"]["region"] == region


def test_every_mapped_region_exists_in_tables():
    from app.services.tender_prompt import CITY_REGION

    assert set(CITY_REGION) <= REGIONS


@pytest.mark.parametrize(
    "text,amount",
    [("£8M", 8e6), ("£12 million", 12e6), ("£750k", 750e3), ("GBP 5,000,000", 5e6), ("worth 25 million", 25e6), ("£10", 10e6)],
)
def test_contract_value_formats(text, amount):
    assert parse(f"Contract {text}.")["form"]["bid_amount_gbp"] == amount


def test_months_become_years():
    assert parse("an 18 month contract")["form"]["duration_years"] == 1.5


def test_planet_and_economy_themes():
    themes = parse("Focus on net zero and local SME supply chain spend")["form"]["themes"]
    assert set(themes) == {"Planet", "Economy"}


def test_missing_fields_are_reported_not_guessed():
    r = parse("We want something good for the community.")
    assert "bid_amount_gbp" not in r["form"]
    assert set(r["missing"]) >= {"bid_amount_gbp", "sv_percent", "duration_years", "region"}


def test_nhs_trust_client():
    f = parse("£8M over 5 years for Leeds Teaching Hospitals NHS Trust, 10% SV")["form"]
    assert f["client"] == "Leeds Teaching Hospitals NHS Trust"
    assert f["duration_years"] == 5
