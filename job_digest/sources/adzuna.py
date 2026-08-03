"""Adzuna Job Search API — https://developer.adzuna.com

Free tier, requires an app_id/app_key pair from developer.adzuna.com.
Queried once per (country, query) pair. Country codes that error out (wrong
code, unsupported market, etc.) are logged and skipped rather than failing
the whole run.
"""
import logging

import requests

from .base import Job

BASE_URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/1"

log = logging.getLogger(__name__)


def search(app_id, app_key, countries, queries, max_days_old=2, results_per_page=50, timeout=20):
    jobs = []
    for country in countries:
        country = country.strip().lower()
        if not country:
            continue
        for query in queries:
            try:
                resp = requests.get(
                    BASE_URL.format(country=country),
                    params={
                        "app_id": app_id,
                        "app_key": app_key,
                        "what": query,
                        "max_days_old": max_days_old,
                        "results_per_page": results_per_page,
                        "sort_by": "date",
                        "content-type": "application/json",
                    },
                    timeout=timeout,
                )
                if resp.status_code != 200:
                    log.warning(
                        "Adzuna %s/%r returned HTTP %s: %s",
                        country, query, resp.status_code, resp.text[:200],
                    )
                    continue
            except requests.RequestException as exc:
                log.warning("Adzuna %s/%r failed: %s", country, query, exc)
                continue

            data = resp.json()
            for item in data.get("results", []):
                job_id = str(item.get("id", ""))
                if not job_id:
                    continue
                company = (item.get("company") or {}).get("display_name", "")
                location = (item.get("location") or {}).get("display_name", "")
                try:
                    latitude = float(item["latitude"]) if item.get("latitude") is not None else None
                    longitude = float(item["longitude"]) if item.get("longitude") is not None else None
                except (TypeError, ValueError):
                    latitude = longitude = None
                jobs.append(
                    Job(
                        source="adzuna",
                        job_id=job_id,
                        title=(item.get("title") or "").strip(),
                        company=company,
                        location=location,
                        date_posted=(item.get("created") or "")[:10],
                        url=item.get("redirect_url", ""),
                        description=item.get("description", ""),
                        latitude=latitude,
                        longitude=longitude,
                    )
                )
    return jobs
