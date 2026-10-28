"""The family's `crawl` task (see scrape.json). Try it without the hub: python crawl.py --local [fiscal_year] The pool worker runs it with the
assignment's env and: SCRAPE_POOL_PROJECT (which project), SCRAPE_JOB_INDEX / SCRAPE_TOTAL_JOBS (this worker's slice), SCRAPE_MAX_HOURS
(time budget), and the project's env: DATASET / RESOURCE (the Finances One dataset and resource ids), COUNTRY (borrower country code).

Each queue item is one World Bank fiscal year. The task pages through the Finances One JSON API (1000 rows per request) for that
year and the borrower country, keeps each raw response in the family's bucket (the hub signs the upload; this code never holds a
storage key), stores one record per (contract, supplier), and reports the standard counters (n_http, t_http_s, http_error,
http_<code>) the hub uses for politeness and tracking. An item is done only when the rows received match the API's own count.
"""
import gzip
import json
import os
import sys
import time

import requests

PROJECT = os.environ.get("SCRAPE_POOL_PROJECT", "")
DATASET = os.environ.get("DATASET", "DS00005")
RESOURCE = os.environ.get("RESOURCE", "RS00005")
COUNTRY = os.environ.get("COUNTRY", "IN")
API = "https://datacatalogapi.worldbank.org/dexapps/fone/api/apiservice"
PAGE = 1000                                                         # the API's maximum `top`
DEADLINE = time.time() + float(os.environ.get("SCRAPE_MAX_HOURS", "1")) * 3600 - 120
UA = "s1d-labs scraper (https://github.com/s1d-labs)"


def query(fiscal_year, skip):
    """Request params for one page of one fiscal year (filter syntax is the API explorer's: field='value' joined by `and`)."""
    return {"datasetId": DATASET, "resourceId": RESOURCE, "type": "json", "top": PAGE, "skip": skip,
            "filter": f"borrower_country_code='{COUNTRY}' and fiscal_year={int(fiscal_year)}"}


def parse(page):
    """(count, [(record_id, data)]) for one API response (JSON text). count is the API's total for the whole query, not this page.
    Pure: test it on saved responses. One contract can have several suppliers (joint ventures), so the id is contract + supplier."""
    doc = json.loads(page)
    out = []
    for row in doc["data"]:
        rid = f"{row['wb_contract_number']}-{row['supplier_id']}"
        out.append((rid, {
            "contract_number": row["wb_contract_number"],
            "borrower_contract_reference": row.get("borrower_contract_reference_number"),
            "contract_description": (row.get("contract_description") or "").strip(),
            "signing_date": row.get("contract_signing_date"),
            "fiscal_year": row.get("fiscal_year"),
            "calendar_year": row.get("contract_signed___calendar_year"),
            "project_id": row.get("project_id"),
            "project_name": row.get("project_name"),
            "global_practice": row.get("project_global_practice"),
            "borrower_country": row.get("borrower_country"),
            "borrower_country_code": row.get("borrower_country_code"),
            "region": row.get("region"),
            "supplier_id": row["supplier_id"],
            "supplier": row.get("supplier"),
            "supplier_country": row.get("supplier_country"),
            "supplier_country_code": row.get("supplier_country_code"),
            "amount_usd": row.get("supplier_contract_amount_usd"),
            "procurement_category": row.get("procurement_category"),
            "procurement_method": row.get("procurement_method"),
            "review_type": row.get("review_type"),
            "as_of_date": row.get("as_of_date"),
        }))
    return doc["count"], out


class LocalHub:
    """Stand-in for HubClient so `--local` runs without the hub: counters go to stderr, records to stdout."""
    settings = {"threads": 1, "delay_ms": 0, "paused": False}

    def __init__(self):
        self.counts = {}

    def metric(self, name, value=1):
        self.counts[name] = self.counts.get(name, 0) + value

    def error(self, n=1):
        self.metric("errors", n)

    def block(self, n=1):
        self.metric("blocked", n)


def fetch(hub, session, params, tries=3):
    """Response text, or None. Retries a refused (429/503) or dropped request a couple of times, waiting as the API asks."""
    for attempt in range(tries):
        t = time.time()
        wait = 10 * (attempt + 1)
        try:
            r = session.get(API, params=params, timeout=120, headers={"User-Agent": UA})
        except requests.RequestException:
            hub.metric("http_error")
            hub.error()
        else:
            hub.metric("n_http")
            hub.metric("t_http_s", time.time() - t)
            if r.status_code == 200:
                return r.text
            hub.metric(f"http_{r.status_code}")
            if r.status_code not in (403, 429, 502, 503, 504):
                return None                                         # e.g. 417 = the API rejected the query: retrying won't help
            if r.status_code in (403, 429, 503):
                hub.block()
            if r.headers.get("Retry-After", "").isdigit():
                wait = int(r.headers["Retry-After"])
        if attempt + 1 < tries:
            time.sleep(min(wait, 60))
    return None


def crawl_year(hub, session, key, fiscal_year):
    """Fetch, upload and store one fiscal year. Returns (rows stored, error or "")."""
    seen, count, skip = set(), None, 0
    while True:
        page = fetch(hub, session, query(fiscal_year, skip))
        if page is None:
            return len(seen), f"request failed at skip={skip}"
        try:
            count, rows = parse(page)
        except (ValueError, KeyError, TypeError) as e:
            return len(seen), f"unexpected response at skip={skip}: {type(e).__name__}"[:200]
        hub.upload_many([(f"api/{key}/skip-{skip:06d}.json.gz", gzip.compress(page.encode()), "application/gzip")])
        for rid, data in rows:
            hub.record(rid, data)
            seen.add(rid)
        skip += PAGE
        if len(rows) < PAGE or skip >= count:
            break
        time.sleep(max(1.0, hub.settings.get("delay_ms", 0) / 1000))
    if len(seen) != count:                                          # rows added or removed while paging: the hub retries later
        return len(seen), f"got {len(seen)} of {count} rows"
    return len(seen), ""


def local(fiscal_year):
    hub = LocalHub()
    session = requests.Session()
    page = fetch(hub, session, query(fiscal_year, 0))
    count, rows = parse(page) if page else (0, [])
    for rid, data in rows:
        print(json.dumps({"record_id": rid, "data": data}, ensure_ascii=False))
    print(f"FY{fiscal_year}: {len(rows)} records on the first page of {count}, counters {hub.counts}", file=sys.stderr)


def main():
    from scrape_hub_client import HubClient      # imported here so --local works without it
    hub = HubClient(PROJECT, job_index=int(os.environ.get("SCRAPE_JOB_INDEX", "0")), total_jobs=int(os.environ.get("SCRAPE_TOTAL_JOBS", "1")))
    session = requests.Session()
    try:
        while time.time() < DEADLINE:
            if hub.settings.get("paused"):
                time.sleep(30)                          # the hub holds us (site down, or the family owner paused it)
                continue
            items = hub.claim(1, steal=True, retry_failed=True)
            if not items:
                break                                   # nothing left for this project: exit, the worker asks the hub for more
            item = items[0]
            n, error = crawl_year(hub, session, item["key"], item["payload"]["fiscal_year"])
            if error:
                hub.complete([item["key"]], "failed", error=error, fetched=n)
            else:
                hub.complete([item["key"]], "done", fetched=n)
            time.sleep(max(1.0, hub.settings.get("delay_ms", 0) / 1000))
        hub.close()
    except BaseException as e:
        hub.close("failed", f"{type(e).__name__}: {e}"[:200])
        raise


if __name__ == "__main__":
    if sys.argv[1:2] == ["--local"]:
        from family import current_fy
        local(int(sys.argv[2]) if len(sys.argv) > 2 else current_fy())
    else:
        main()
