"""Bundesagentur für Arbeit Jobsuche API — public, no signup required.

The search endpoint does not return full description text, only title /
occupation fields, so scoring for these jobs relies on that shorter text.
"""
import logging

import requests

from .base import Job

BASE_URL = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v6/jobs"
API_KEY = "jobboerse-jobsuche"
DETAIL_URL = "https://www.arbeitsagentur.de/jobsuche/jobdetail/{ref}"

log = logging.getLogger(__name__)


def search(queries, wo="Deutschland", days_old=3, size=100, timeout=20):
    """Run each query against the BA Jobsuche API and return a flat list of Job."""
    jobs = []
    for query in queries:
        try:
            resp = requests.get(
                BASE_URL,
                headers={"X-API-Key": API_KEY},
                params={
                    "was": query,
                    "wo": wo,
                    "veroeffentlichtseit": days_old,
                    "size": size,
                    "page": 1,
                },
                timeout=timeout,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            log.warning("Bundesagentur query %r failed: %s", query, exc)
            continue

        data = resp.json()
        for item in data.get("ergebnisliste", []):
            ref = item.get("referenznummer")
            if not ref:
                continue
            locations = item.get("stellenlokationen") or [{}]
            loc0 = locations[0]
            ort = (loc0.get("adresse") or {}).get("ort", "")
            jobs.append(
                Job(
                    source="arbeitsagentur",
                    job_id=ref,
                    title=item.get("stellenangebotsTitel", "").strip(),
                    company=item.get("firma", "").strip(),
                    location=ort,
                    date_posted=item.get("datumErsteVeroeffentlichung", ""),
                    url=DETAIL_URL.format(ref=ref),
                    description=" ".join(item.get("alleBerufe", []) or []),
                    latitude=loc0.get("breite"),
                    longitude=loc0.get("laenge"),
                )
            )
    return jobs
