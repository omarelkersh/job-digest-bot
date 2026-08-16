"""Accumulates scored jobs (across every run, every market) into docs/jobs.json
for the browsable portal (docs/index.html, served via GitHub Pages). This is a
superset of what gets emailed — the email caps at MAX_JOBS_PER_EMAIL, the feed
keeps everything that cleared MIN_SCORE.
"""
import json
import os
from datetime import datetime, timedelta

FEED_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "jobs.json")
FEED_RETENTION_DAYS = 60


class JobFeed:
    def __init__(self, path=FEED_PATH):
        self.path = path
        self._jobs = self._load()

    def _load(self):
        if not os.path.exists(self.path):
            return {}
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {j["id"]: j for j in data.get("jobs", []) if "id" in j}
        except (json.JSONDecodeError, KeyError):
            return {}

    def add(self, market_key, market_label, scored_job, now_iso):
        j = scored_job.job
        key = f"{market_key}:{j.dedup_key}"
        existing = self._jobs.get(key)
        self._jobs[key] = {
            "id": key,
            "market": market_key,
            "market_label": market_label,
            "source": j.source,
            "title": j.title,
            "company": j.company,
            "location": j.location,
            "url": j.url,
            "date_posted": j.date_posted,
            "description": (j.description or "")[:2000],
            "score": scored_job.score,
            "matched_skills": scored_job.matched_skills,
            "matched_role": scored_job.matched_role,
            "matched_visa": scored_job.matched_visa,
            "distance_km": scored_job.distance_km,
            "first_seen": existing["first_seen"] if existing else now_iso,
        }

    def save(self, now):
        cutoff = now - timedelta(days=FEED_RETENTION_DAYS)
        pruned = {}
        for key, job in self._jobs.items():
            try:
                first_seen = datetime.fromisoformat(job["first_seen"])
            except (KeyError, ValueError):
                pruned[key] = job
                continue
            if first_seen >= cutoff:
                pruned[key] = job
        self._jobs = pruned

        jobs_list = sorted(self._jobs.values(), key=lambda j: j["first_seen"], reverse=True)

        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(
                {"generated_at": now.isoformat(), "jobs": jobs_list},
                f, indent=2, ensure_ascii=False, sort_keys=False,
            )
            f.write("\n")
