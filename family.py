"""What this family scrapes. Change this file first.

FAMILY must equal the repo name (s1d-labs/<FAMILY>) and the family the hub owner added on scrape.s1d.me/runners.
Each project is one queue of work on one site; `target` is the host it hits (the hub caps workers per target).

Source: World Bank Finances One, "Contract Awards in Investment Project Financing (Since FY 2020)" (DS00005, formerly the
finances.worldbank.org "Major Contract Awards" dataset kdui-wcs3). finances.worldbank.org now redirects to financesone; the data
comes from its JSON API (datacatalogapi.worldbank.org), filtered to borrower country India. Older awards (FY2001-FY2016, prior
review only, no supplier ids) are a separate dataset, DS01004, not covered here.
"""
import datetime
import json
from pathlib import Path

FAMILY = json.loads((Path(__file__).parent / "scrape.json").read_text())["family"]

API = "https://datacatalogapi.worldbank.org/dexapps/fone/api/apiservice"
FIRST_FY = 2020                                  # the dataset starts at FY2020


def current_fy(today=None):
    """World Bank fiscal year: July to June, named after the year it ends in."""
    today = today or datetime.date.today()
    return today.year + 1 if today.month >= 7 else today.year


# India rows per fiscal year when this was written (2026-10): only for progress and ETAs on the dashboard
EXPECTED = {2020: 4989, 2021: 6925, 2022: 5425, 2023: 5390, 2024: 4920, 2025: 4545, 2026: 2765, 2027: 65}

PROJECTS = [
    {
        "name": f"{FAMILY}-contracts-india",      # project names: 2-64 chars of a-z 0-9 - _, start them with the family name
        "title": "World Bank contract awards (India projects)",
        "task": "crawl",                         # a task from scrape.json
        "target": "datacatalogapi.worldbank.org",
        "env": {"DATASET": "DS00005", "RESOURCE": "RS00005", "COUNTRY": "IN"},
        "probe": f"{FAMILY}:datacatalogapi.worldbank.org",
        "max_workers": 2,                        # ~40 API calls in all: more workers would only add load
        "unit_label": "fiscal year", "record_label": "contract award",
        # the queue: one item per fiscal year; the task pages through it (1000 rows per request) and checks the total
        "items": [{"key": f"fy{fy}", "payload": {"fiscal_year": fy, "expected": EXPECTED.get(fy, 3000)}}
                  for fy in range(FIRST_FY, current_fy() + 1)],
    },
]

# health checks the hub runs every minute; work for a project holds while its probe fails
PROBES = [{"name": f"{FAMILY}:datacatalogapi.worldbank.org", "url": f"{API}?datasetId=DS00005&resourceId=RS00005&type=json&top=1",
           "expect": "wb_contract_number"}]
