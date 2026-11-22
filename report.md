# World Bank contract awards, India: scrape report

Job **P18** · family `world-bank` · project `world-bank-contracts-india` · status as of 2026-10-29

## Contents

1. [Summary](#1-summary)
2. [Where everything is](#2-where-everything-is)
3. [What we have](#3-what-we-have)
   - [3.1 Source](#31-source)
   - [3.2 Coverage and counts](#32-coverage-and-counts)
   - [3.3 Breakdowns](#33-breakdowns)
   - [3.4 Fields](#34-fields)
   - [3.5 How the scrape ran](#35-how-the-scrape-ran)
4. [What we don't have](#4-what-we-dont-have)
5. [Next steps](#5-next-steps)
6. [Notes for using the data](#6-notes-for-using-the-data)
7. [Repository files](#7-repository-files)

---

## 1. Summary

- **35,024 contract awards** for World Bank projects in India, fiscal years FY2020 to FY2027 (signed 1 Jul 2019 to 14 Oct 2026).
- These cover 34,524 contracts, 127 World Bank projects and 11,004 suppliers, worth **US$9.04 bn** in total.
- Each record has the job's fields (project, contract, supplier, amount, method) and 16 more.
- The stored rows match the source's own count exactly, for each year and in total. No errors and no blocked requests.
- **Gaps:**
  - Contracts signed before FY2020: FY2001–FY2016 are in a separate dataset, and FY2017–FY2019 aren't in either dataset.
  - New contracts after 29 Oct 2026: the scrape ran once and doesn't refresh yet.

## 2. Where everything is

| What | Where |
|---|---|
| Records, one column per field | Postgres `scrape_hub`, view `projects.world_bank_contracts_india` (all columns are `text`, so cast `amount_usd` to `numeric`) |
| Records as raw JSON | `scrape_hub.public.records` where `project = 'world-bank-contracts-india'` (`record_id`, `data` jsonb) |
| Records in Metabase | https://metabase.s1d.me → Team data (scrape_hub), schema `projects`, table `world_bank_contracts_india` |
| Raw API responses | bucket `s1d-labs-ansh`, `world-bank-contracts-india/api/fy<YYYY>/skip-<NNNNNN>.json.gz`: 38 files, 2.4 MB (`mybucket ls world-bank-contracts-india/api/`) |
| Queue, runs, speed | https://scrape.s1d.me → Runs → `world-bank-contracts-india` |
| Scraper code | https://github.com/s1d-labs/world-bank (see [section 7](#7-repository-files)) |
| Source dataset page | https://financesone.worldbank.org/contract-awards-in-investment-project-financing/DS00005 |
| Source API | `https://datacatalogapi.worldbank.org/dexapps/fone/api/apiservice?datasetId=DS00005&resourceId=RS00005&type=json` |

Example query:

```sql
select project_id, project_name, supplier, amount_usd::numeric, procurement_method, signing_date
from projects.world_bank_contracts_india
order by amount_usd::numeric desc
limit 20;
```

## 3. What we have

### 3.1 Source

The job names the "Major Contract Awards" dataset on `finances.worldbank.org`. That site now redirects to **Finances One**
(`financesone.worldbank.org`), where the dataset continues as **DS00005, "Contract Awards in Investment Project Financing (Since
FY 2020)"**. Its metadata still lists the old dataset id `kdui-wcs3`. The old Socrata API (`/resource/kdui-wcs3.json`) no longer works.

From the dataset's description:

- It covers **all** contract awards financed by the World Bank under Investment Project Financing since FY2020, both prior and post
  review.
- The data comes from STEP (Systematic Tracking of Exchanges in Procurement), and borrowers enter it themselves. The World Bank
  doesn't guarantee it.
- "Supplier country" is where the supplier is registered, which may not be where it's from.
- It doesn't include awards to subcontractors, and it doesn't account for cofinancing.
- For joint ventures, the contract value is **split equally** among the members.
- It's updated daily and published under the Creative Commons Attribution 4.0 licence.

We query it through the public JSON API (no key needed): filter `borrower_country_code='IN' and fiscal_year=<FY>`, 1,000 rows per request.

### 3.2 Coverage and counts

World Bank fiscal years run July to June: FY2024 = 1 Jul 2023 – 30 Jun 2024.

| Fiscal year | Records | US$ m | Source count | Match |
|---|---:|---:|---:|:-:|
| FY2020 | 4,989 | 2,889.7 | 4,989 | ✓ |
| FY2021 | 6,925 | 1,907.6 | 6,925 | ✓ |
| FY2022 | 5,425 | 1,527.1 | 5,425 | ✓ |
| FY2023 | 5,390 | 653.5 | 5,390 | ✓ |
| FY2024 | 4,920 | 702.7 | 4,920 | ✓ |
| FY2025 | 4,545 | 666.5 | 4,545 | ✓ |
| FY2026 | 2,765 | 598.3 | 2,765 | ✓ |
| FY2027 (in progress) | 65 | 94.2 | 65 | ✓ |
| **Total** | **35,024** | **9,039.7** | **35,024** | ✓ |

Checks on the stored data:

- All records have borrower country India.
- No amounts are missing, zero or negative.
- Record ids are unique.
- All rows have the source's as-of date of 29 Oct 2026.

### 3.3 Breakdowns

**By procurement category**

| Category | Records | US$ m |
|---|---:|---:|
| Works | 22,511 | 6,940.0 |
| Goods | 10,238 | 1,236.8 |
| Consultant Services | 1,826 | 722.4 |
| Non-consulting Services | 449 | 140.4 |

**By procurement method**

| Method | Records | US$ m |
|---|---:|---:|
| Request for Bids | 5,170 | 6,754.1 |
| Direct Selection | 2,540 | 695.5 |
| Quality And Cost-Based Selection | 679 | 511.7 |
| Request for Proposals | 11 | 490.0 |
| Public Private Partnership | 10 | 239.7 |
| Request for Quotations | 25,759 | 237.9 |
| Fixed Budget Selection | 54 | 43.6 |
| Consultant Qualification Selection | 137 | 26.2 |
| Quality Based Selection | 19 | 15.1 |
| Least Cost Selection | 90 | 14.7 |
| Individual Consultant Selection | 541 | 9.0 |
| UN Agencies (Direct) | 1 | 1.4 |
| Community Driven Development | 13 | 0.7 |

**By review type**

- **Prior review:** 615 records, US$5,312.6 m.
- **Post review:** 34,405 records, US$3,726.5 m.
- **Blank:** 4 records, US$0.5 m.

So most of the money is in a few large prior-reviewed contracts, while most of the records are small post-reviewed purchases.

**By supplier country**

- **Registered in India:** 34,844 records, US$8,524.8 m.
- **Registered elsewhere:** 180 records, US$514.8 m.

**Top 10 projects by awarded value**

| Project | Name | Records | US$ m |
|---|---|---:|---:|
| P173836 | India COVID-19 Emergency Response and Health Systems Preparedness | 1,353 | 666.0 |
| P130544 | Karnataka Urban Water Supply Modernization Project | 17 | 583.7 |
| P167350 | Green National Highways Corridor Project | 47 | 492.3 |
| P169111 | Second National Ganga River Basin Project | 45 | 485.9 |
| P162679 | West Bengal Major Irrigation and Flood Management Project | 242 | 432.5 |
| P124639 | PMGSY Rural Roads Project | 595 | 358.1 |
| P170590 | West Bengal Electricity Distribution Grid Modernization Project | 50 | 325.6 |
| P119085 | National Ganga River Basin Project | 15 | 309.5 |
| P170811 | Punjab Municipal Services Improvement Project | 51 | 295.3 |
| P162086 | Jharkhand Power System Improvement Project | 25 | 210.3 |

### 3.4 Fields

There is one record per **contract and supplier**. The record id is `<contract_number>-<supplier_id>`, for example `1734565-730832`.
A joint-venture contract therefore has one record per member.

| Field | Source column | Meaning |
|---|---|---|
| `contract_number` | `wb_contract_number` | World Bank contract number |
| `borrower_contract_reference` | `borrower_contract_reference_number` | Borrower's own reference, e.g. `IN-OCTDMS-320529-CS-QCBS` |
| `contract_description` | `contract_description` | What the contract is for |
| `signing_date` | `contract_signing_date` | `DD-Mon-YYYY` |
| `fiscal_year` | `fiscal_year` | World Bank FY of signing |
| `calendar_year` | `contract_signed___calendar_year` | Calendar year of signing |
| `project_id` | `project_id` | World Bank project id (`P…`) |
| `project_name` | `project_name` | |
| `global_practice` | `project_global_practice` | Sector(s), `;`-separated |
| `borrower_country`, `borrower_country_code` | same | Always India / `IN` here |
| `region` | `region` | South Asia |
| `supplier_id` | `supplier_id` | Supplier id in STEP. Numeric, or a 16-character hex id for anonymised individual consultants |
| `supplier` | `supplier` | Supplier name, as the borrower entered it |
| `supplier_country`, `supplier_country_code` | same | Where the supplier is registered |
| `amount_usd` | `supplier_contract_amount_usd` | This supplier's share of the contract in US$ (JV value split equally) |
| `procurement_category` | `procurement_category` | Works / Goods / Consultant Services / Non-consulting Services |
| `procurement_method` | `procurement_method` | See [3.3](#33-breakdowns) |
| `review_type` | `review_type` | Prior / Post (World Bank review before or after award) |
| `as_of_date` | `as_of_date` | Date of the source's data snapshot |

### 3.5 How the scrape ran

- **Setup:** the workflow ran on 2026-10-29 at 13:21 UTC and registered the project, the health check and 8 queue items, one per
  fiscal year.
- **Runs:** two workers ran on `Sarthak-Sidhant/scrape-runner` from 13:22 to 13:27 UTC, about 4 minutes.
- **Results:** every item was done on the first attempt, with 0 errors and 0 blocked requests.
- **Requests:** 38 requests to the API, about 0.5 s each, at most 2 workers (`max_workers: 2`).
- **Completeness check:** an item is marked done only when the rows received equal the API's `count` for that year. If they don't,
  the item fails and the hub retries it.

## 4. What we don't have

| Gap | Size | Why | Fix |
|---|---|---|---|
| Awards **FY2001–FY2016** | 5,584 India rows | A separate dataset, DS01004 ("since FY 2001 – FY 2016", prior review only, last updated Mar 2022). It has **no supplier id** and uses a different `contract_number` / `supplier_contract_amount` schema | [Next step 2](#5-next-steps) |
| Awards **FY2017–FY2019** | unknown | In **neither** dataset: DS00005 returns 0 India rows for these years and DS01004 ends at FY2016 | [Next step 3](#5-next-steps) |
| Post-review awards **before FY2020** | unknown | DS01004 has prior-reviewed contracts only | Same as the line above |
| Awards **after 29 Oct 2026** | about 3,000–5,000 a year | The source updates daily, but each queue item runs once. Re-running setup adds only *new* fiscal years | [Next step 1](#5-next-steps) |
| Changes and removals in the source | unknown | Records upsert by id, so a corrected row overwrites the old one on the next refresh, but a row the source deletes stays in our data | Next step 1 (compare ids per FY) |
| Subcontracts and cofinancing | — | Not in the source | None |
| Names of individual consultants | 541 records | Anonymised in the source (hex `supplier_id`, supplier "INDIVIDUAL CONSULTANT") | None |
| Project details (state, status, commitment, dates) | 127 projects | Not in this dataset | [Next step 4](#5-next-steps) |
| Clean supplier identities | 11,004 supplier ids | Names are free text entered by borrowers, so the same firm can appear under several ids or spellings | [Next step 5](#5-next-steps) |
| Amounts in local currency (INR) | — | The source gives US$ only | None |

## 5. Next steps

These are proposed, in priority order; none of them have been started yet.

1. **Keep it current.** Add a scheduled workflow (for example weekly) that queues fresh items for the current and previous fiscal
   year. The hub keeps done keys, so these need dated keys, e.g. `fy2027-r2026-11-05`. Records are upserted, so corrections overwrite
   older versions. Also log the API's count per year, so that rows removed at the source can be spotted.
2. **Add FY2001–FY2016 (DS01004)** as a second project, `world-bank-contracts-india-historical`, in the same family. This needs its
   own record id, because there's no `supplier_id`: use `contract_number` plus a short hash of the supplier name. It's about 5,600 rows
   and about 6 requests.
3. **Look for an FY2017–FY2019 source.** Check whether World Bank procurement notices / contract award data elsewhere (e.g. the
   projects API at `search.worldbank.org`) cover these years for India. If none does, record it as a known gap.
4. **Enrich projects.** Fetch the 127 projects' details (state/location, status, approval and closing dates, commitment) from the
   World Bank Projects API and store them as a small `world-bank-projects-india` project to join on `project_id`.
5. **Normalise suppliers.** Group supplier ids and name variants, for example by normalised name plus country. Do this in
   `ws_ansh` as a derived table, not in the scraped records.

## 6. Notes for using the data

- **Amounts:** cast `amount_usd` to `numeric`, because the view's columns are text. Summing `amount_usd` over all records gives
  the total awarded value without double counting, because joint-venture values are already split among the members.
- **Counting:**
  - To count *contracts*, use `count(distinct contract_number)`. There are 34,524 contracts and 35,024 records.
  - To count *suppliers*, remember that one firm can have several ids (see [section 4](#4-what-we-dont-have)).
- **Dates:** `signing_date` is text like `07-Jul-2023`. Parse it with `to_date(signing_date, 'DD-Mon-YYYY')`.
- **Fiscal years:** `fiscal_year` is the World Bank FY, not the Indian financial year (April to March) and not the calendar year.
  `calendar_year` is also available.
- **Licence:** Creative Commons Attribution 4.0. Credit "World Bank, Finances One" when publishing anything derived from it.

## 7. Repository files

| File | Purpose |
|---|---|
| [`scrape.json`](scrape.json) | Family name, setup step, task `crawl` → `python crawl.py` |
| [`family.py`](family.py) | Project definition: target, env (`DATASET`, `RESOURCE`, `COUNTRY`), one queue item per FY from FY2020, health check |
| [`setup_family.py`](setup_family.py) | Registers the project, pool entry and health check, and seeds the queue (run by the **setup** workflow) |
| [`crawl.py`](crawl.py) | The task: `parse()` (pure), `fetch()` (retries 429/5xx politely), `crawl_year()` (pages through one FY and checks the count). `python crawl.py --local 2024` runs it without the hub |
| [`tests/test_parse.py`](tests/test_parse.py) | Parsing tests on a saved API response ([`tests/pages/india-fy2024-page1.json`](tests/pages/india-fy2024-page1.json)) |
| [`.github/workflows/check.yml`](.github/workflows/check.yml) | Runs on every push: tests and `scrape-check --items 2` |
| [`.github/workflows/setup.yml`](.github/workflows/setup.yml) | Manual: applies `family.py` to the hub |
| [`README.md`](README.md) | Short description of the family |
| [`CLAUDE.md`](CLAUDE.md) | The scrape pool's technical reference |
