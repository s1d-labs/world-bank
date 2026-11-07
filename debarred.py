#!/usr/bin/env python3
"""The family's `debarred` task: the World Bank's public "Listing of Ineligible (Debarred & Cross-Debarred) Firms and
Individuals" (worldbank.org/en/projects-operations/procurement/debarred-firms).

The page draws the list in the browser from the Bank's public gateway. This task opens that public page headlessly and keeps the
one data response the page itself requests (endpoint .../FIRM/SANCTIONED_FIRM, under `response.ZPROCSUPP`); the browser sends the
page's own request, this task adds no key. One queue item (the list); one record per listed party; the raw response goes to the
family bucket. Try it without the hub:  python debarred.py --local   (needs Chromium; the family `setup` installs it.)
"""
import gzip
import json
import os
import sys
import time

URL = "https://www.worldbank.org/en/projects-operations/procurement/debarred-firms"
DEADLINE = time.time() + float(os.environ.get("SCRAPE_MAX_HOURS", "1")) * 3600 - 60


def fetch_listing():
    """Render the public page and return the raw JSON text of its sanctioned-firm response. Pure fetch; no hub."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--no-sandbox"])
        try:
            pg = b.new_page()
            with pg.expect_response(lambda r: "SANCTIONED_FIRM" in r.url and r.status == 200, timeout=90000) as ri:
                pg.goto(URL, wait_until="domcontentloaded", timeout=90000)
            return ri.value.text()
        finally:
            b.close()


def parse(text):
    """(raw_text, [(record_id, data)]) from the sanctioned-firm JSON. Pure: testable on a saved response."""
    doc = json.loads(text)
    firms = doc["response"]["ZPROCSUPP"]
    out = []
    for f in firms:
        sid = f.get("SUPP_ID")
        if sid is None:
            continue
        name = " ".join(" ".join(filter(None, [f.get("SUPP_PRE_ACRN"), f.get("SUPP_NAME"), f.get("SUPP_POST_ACRN")])).split())
        out.append((str(sid), {
            "supp_id": sid,
            "name": name or (f.get("SUPP_NAME") or "").strip(),
            "type": "individual" if f.get("SUPP_TYPE_CODE") == "I" else "firm",
            "country": f.get("COUNTRY_NAME"),
            "country_code": f.get("LAND1"),
            "state": f.get("SUPP_PROV_NAME") or f.get("SUPP_STATE_CODE"),
            "city": f.get("SUPP_CITY"),
            "address": f.get("SUPP_ADDR"),
            "from_date": None if (f.get("DEBAR_FROM_DATE") or "").startswith("2999") else f.get("DEBAR_FROM_DATE"),
            "to_date": None if (f.get("DEBAR_TO_DATE") or "").startswith("2999") else f.get("DEBAR_TO_DATE"),
            "ongoing": (f.get("DEBAR_TO_DATE") or "").startswith("2999"),
            "grounds": f.get("DEBAR_REASON"),
            "debar_type": f.get("DEBAR_TYPE"),          # O = debarment with conditional release, etc.
            "cross_debarred": f.get("DEBAR_TYPE") == "C" or (f.get("CRPD_STAT") or "") not in ("", None),
            "ineligibility": f.get("INELIG_FLG"),
            "additional_info": f.get("ADD_SUPP_INFO"),
            "last_refresh": f.get("LAST_REFRESH_DATE"),
        }))
    return text, out


def run(hub):
    text = fetch_listing()
    _, rows = parse(text)
    if len(rows) < 100:                                  # the list has ~1,500 parties; far fewer means the response changed
        raise ValueError(f"only {len(rows)} parties parsed; aborting rather than storing a short list")
    hub.upload_many([("debarred/sanctioned_firm.json.gz", gzip.compress(text.encode("utf8")), "application/gzip")])
    for rid, data in rows:
        hub.record(rid, data)
    return len(rows)


class LocalHub:
    settings = {"threads": 1, "delay_ms": 0, "paused": False}

    def __init__(self):
        self.n = 0

    def upload_many(self, files):
        print(f"[local] would upload {len(files)} file(s)", file=sys.stderr)

    def record(self, rid, data):
        self.n += 1
        if self.n <= 5:
            print(json.dumps({"record_id": rid, "data": data}, ensure_ascii=False))


def main():
    from scrape_hub_client import HubClient
    hub = HubClient(os.environ.get("SCRAPE_POOL_PROJECT", ""),
                    job_index=int(os.environ.get("SCRAPE_JOB_INDEX", "0")),
                    total_jobs=int(os.environ.get("SCRAPE_TOTAL_JOBS", "1")))
    try:
        items = hub.claim(1, steal=True, retry_failed=True)
        if items:
            it = items[0]
            try:
                n = run(hub)
                hub.complete([it["key"]], "done", fetched=n)
            except Exception as e:  # noqa: BLE001
                hub.complete([it["key"]], "failed", error=f"{type(e).__name__}: {e}"[:200])
        hub.close()
    except BaseException as e:
        hub.close("failed", f"{type(e).__name__}: {e}"[:200])
        raise


if __name__ == "__main__":
    if sys.argv[1:2] == ["--local"]:
        total = run(LocalHub())
        print(f"debarred: {total} records", file=sys.stderr)
    else:
        main()
