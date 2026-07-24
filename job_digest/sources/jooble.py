"""Jooble REST API — https://jooble.org/api/about

Free API key, single global endpoint (POST https://jooble.org/api/{key}) with
a free-text `location` field — this is what covers the Gulf market, since
Adzuna does not operate there.
"""
import logging

import requests

from .base import Job

URL_TEMPLATE = "https://jooble.org/api/{key}"

log = logging.getLogger(__name__)


def search(api_key, locations, queries, results_on_page=20, timeout=20):
    jobs = []
    url = URL_TEMPLATE.format(key=api_key)
    for location in locations:
        location = location.strip()
        if not location:
            continue
        for query in queries:
            try:
                resp = requests.post(
                    url,
                    json={
                        "keywords": query,
                        "location": location,
                        "page": 1,
                        "ResultOnPage": results_on_page,
                    },
                    timeout=timeout,
                )
                if resp.status_code != 200:
                    log.warning(
                        "Jooble %s/%r returned HTTP %s: %s",
                        location, query, resp.status_code, resp.text[:200],
                    )
                    continue
            except requests.RequestException as exc:
                log.warning("Jooble %s/%r failed: %s", location, query, exc)
                continue

            data = resp.json()
            for item in data.get("jobs", []):
                link = item.get("link", "")
                job_id = str(item.get("id") or link)
                if not job_id:
                    continue
                jobs.append(
                    Job(
                        source="jooble",
                        job_id=job_id,
                        title=(item.get("title") or "").strip(),
                        company=item.get("company", "") or "",
                        location=item.get("location", "") or location,
                        date_posted=(item.get("updated") or "")[:10],
                        url=link,
                        description=item.get("snippet", "") or "",
                    )
                )
    return jobs
