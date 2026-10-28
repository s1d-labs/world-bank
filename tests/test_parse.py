"""Parsing tests on a saved API response: fast, no network. Add a saved response for every shape the API returns."""
import json
from pathlib import Path

import crawl
import family

PAGES = Path(__file__).parent / "pages"


def test_api_page_gives_one_record_per_contract_supplier():
    count, rows = crawl.parse((PAGES / "india-fy2024-page1.json").read_text(encoding="utf-8"))
    assert count == 4920                                            # the API's total for the query, not this page
    assert len(rows) == 20
    rid, award = rows[0]
    assert rid == "1734565-730832"                                  # WB contract number + supplier id: stable across runs
    assert award["project_id"] == "P163533" and award["supplier"] == "SYNERGY TECHNOFIN PVT"
    assert award["amount_usd"] == 413722.51 and award["procurement_method"] == "Quality And Cost-Based Selection"
    assert award["borrower_country_code"] == "IN" and award["fiscal_year"] == 2024
    assert len({r for r, _ in rows}) == 20                          # no duplicate ids on a page


def test_an_empty_year_gives_nothing():
    assert crawl.parse(json.dumps({"count": 0, "data": []})) == (0, [])


def test_query_filters_country_and_year():
    q = crawl.query(2024, 3000)
    assert q["filter"] == "borrower_country_code='IN' and fiscal_year=2024"
    assert q["top"] == 1000 and q["skip"] == 3000 and q["datasetId"] == "DS00005"


def test_fiscal_year_runs_july_to_june():
    import datetime
    assert family.current_fy(datetime.date(2026, 6, 30)) == 2026
    assert family.current_fy(datetime.date(2026, 7, 1)) == 2027
