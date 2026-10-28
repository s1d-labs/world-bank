# world-bank

s1d-labs scrape pool family: **World Bank contract awards for India projects** (job P18).

| | |
|---|---|
| Source | [Finances One: Contract Awards in Investment Project Financing (Since FY 2020)](https://financesone.worldbank.org/contract-awards-in-investment-project-financing/DS00005), dataset DS00005 (the old finances.worldbank.org "Major Contract Awards", `kdui-wcs3`; that site now redirects here) |
| API | `https://datacatalogapi.worldbank.org/dexapps/fone/api/apiservice?datasetId=DS00005&resourceId=RS00005&type=json&top=1000&skip=N&filter=borrower_country_code='IN' and fiscal_year=YYYY` (public, no key, 1000 rows max per call) |
| Project | `world-bank-contracts-india`: one queue item per World Bank fiscal year (FY2020 to the current one, July to June) |
| Record | one per contract and supplier, id `<wb_contract_number>-<supplier_id>` (joint ventures have several suppliers per contract): project, contract, supplier, amount (USD), procurement method/category, dates, review type |
| Files | each raw API response, gzipped, at `world-bank-contracts-india/api/fy<YYYY>/skip-<N>.json.gz` |
| Size | about 35,000 rows from about 40 requests (2026-10) |

An item counts as done only when the rows received match the API's `count` for that year. If they don't (for example, rows added
while paging), the item fails and the hub retries it. Re-running setup adds a new fiscal year when one starts. Years already done are
not fetched again unless they are re-queued.

Not covered: awards from FY2001 to FY2016 (dataset DS01004, prior review only). That dataset has no supplier ids, so it would need a
different record id.

Try one page without the hub: `python crawl.py --local 2024`. Tests: `python -m pytest tests`. Full check: `scrape-check`.

## What your code gets

The pool worker ([s1d-labs/runner](https://github.com/s1d-labs/runner)) checks out this repo at `main`, runs the `setup` steps from
`scrape.json`, and for each assignment runs the task's command here with:

| Variable | What |
|---|---|
| `SCRAPE_POOL_PROJECT` | the project to work on |
| `SCRAPE_JOB_INDEX`, `SCRAPE_TOTAL_JOBS` | this worker's slice |
| `SCRAPE_MAX_HOURS` | how long the command may run |
| `SCRAPE_HUB_URL` | the hub |
| your project's `env` | e.g. `SITE` |

Use `scrape_hub_client` (`HubClient`) to claim queue items, store records, upload files and report counters. Exit when there is
nothing left; the worker then asks the hub for the next assignment.

## Rules (the full contract is in CLAUDE.md, written for people and for Claude Code)

- **Be polite.** Use `hub.settings["threads"]` and `delay_ms`, idle while `hub.settings["paused"]`, and report `n_http` and
  `t_http_s` for every request and `http_<code>` / `http_error` for failures: the hub throttles you from these.
- **Files go through the hub** (`hub.upload_many`): it signs each upload into the family's bucket (500 GB per member) and stops at
  the cap. Never put storage keys in this repo.
- **Public data only**; read the site's terms first. See the team docs on home.s1d.me (Scraping rules).
