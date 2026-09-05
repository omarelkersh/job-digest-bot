import logging
import os

from . import config, feed, scoring, store
from .sources import adzuna, arbeitsagentur, jooble

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("job_digest")

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "seen_jobs.json")
DRY_RUN = os.environ.get("DRY_RUN", "").lower() in ("1", "true", "yes")


def gather_europe_jobs():
    jobs = arbeitsagentur.search(config.EUROPE_ROLE_QUERIES)
    log.info("Bundesagentur: %d raw results", len(jobs))

    adzuna_app_id = os.environ.get("ADZUNA_APP_ID")
    adzuna_app_key = os.environ.get("ADZUNA_APP_KEY")
    if adzuna_app_id and adzuna_app_key:
        adzuna_jobs = adzuna.search(
            adzuna_app_id, adzuna_app_key,
            config.ADZUNA_EUROPE_COUNTRIES, config.EUROPE_ROLE_QUERIES,
        )
        log.info("Adzuna (Europe): %d raw results", len(adzuna_jobs))
        jobs += adzuna_jobs
    else:
        log.warning("ADZUNA_APP_ID/ADZUNA_APP_KEY not set — skipping Adzuna for Europe digest")

    return jobs


def gather_europe_fulltime_jobs():
    jobs = []

    adzuna_app_id = os.environ.get("ADZUNA_APP_ID")
    adzuna_app_key = os.environ.get("ADZUNA_APP_KEY")
    if adzuna_app_id and adzuna_app_key:
        adzuna_jobs = adzuna.search(
            adzuna_app_id, adzuna_app_key,
            config.ADZUNA_FULLTIME_COUNTRIES, config.EUROPE_FULLTIME_ROLE_QUERIES,
        )
        log.info("Adzuna (Europe Full-Time): %d raw results", len(adzuna_jobs))
        jobs += adzuna_jobs
    else:
        log.warning("ADZUNA_APP_ID/ADZUNA_APP_KEY not set — skipping Adzuna for Europe Full-Time digest")

    # Adzuna's Ireland ("ie") support isn't confirmed, so Jooble covers the
    # same countries by location string as a redundant backup.
    jooble_key = os.environ.get("JOOBLE_API_KEY")
    if jooble_key:
        jooble_jobs = jooble.search(
            jooble_key, config.JOOBLE_FULLTIME_LOCATIONS, config.EUROPE_FULLTIME_ROLE_QUERIES,
        )
        log.info("Jooble (Europe Full-Time): %d raw results", len(jooble_jobs))
        jobs += jooble_jobs
    else:
        log.warning("JOOBLE_API_KEY not set — skipping Jooble for Europe Full-Time digest")

    return jobs


def gather_gulf_jobs():
    jooble_key = os.environ.get("JOOBLE_API_KEY")
    if not jooble_key:
        log.warning("JOOBLE_API_KEY not set — skipping Gulf digest entirely")
        return []
    jobs = jooble.search(jooble_key, config.GULF_LOCATIONS, config.GULF_ROLE_QUERIES)
    log.info("Jooble (Gulf): %d raw results", len(jobs))
    return jobs


def gather_remote_jobs():
    adzuna_app_id = os.environ.get("ADZUNA_APP_ID")
    adzuna_app_key = os.environ.get("ADZUNA_APP_KEY")
    if not (adzuna_app_id and adzuna_app_key):
        log.warning("ADZUNA_APP_ID/ADZUNA_APP_KEY not set — skipping Remote digest entirely")
        return []
    jobs = adzuna.search(
        adzuna_app_id, adzuna_app_key,
        config.ADZUNA_REMOTE_COUNTRIES, config.REMOTE_ROLE_QUERIES,
    )
    log.info("Adzuna (Remote): %d raw results", len(jobs))
    return jobs


GATHERERS = {
    "europe": gather_europe_jobs,
    "europe_fulltime": gather_europe_fulltime_jobs,
    "gulf": gather_gulf_jobs,
    "remote": gather_remote_jobs,
}


def dedupe(jobs):
    seen_keys = set()
    unique = []
    for j in jobs:
        if j.dedup_key in seen_keys:
            continue
        seen_keys.add(j.dedup_key)
        unique.append(j)
    return unique


def run_market(market_key, seen_store, job_feed, now):
    market = config.MARKETS[market_key]
    raw_jobs = GATHERERS[market_key]()
    jobs = dedupe(raw_jobs)

    # Dedup keys are market-scoped — a job already sent in one digest can
    # still legitimately appear in another (e.g. a remote-tagged posting
    # relevant to both the Werkstudent and Remote digests).
    new_jobs = [j for j in jobs if seen_store.is_new(f"{market_key}:{j.dedup_key}")]
    log.info("[%s] %d unique / %d new (not previously seen)", market_key, len(jobs), len(new_jobs))

    scored_all = scoring.score_and_rank(
        new_jobs,
        fulltime_only=market.get("fulltime_only", False),
        allow_easy_roles=market.get("allow_easy_roles", False),
        require_remote=market.get("require_remote", False),
        require_role_match=market.get("require_role_match", False),
    )
    log.info("[%s] %d passed scoring threshold (MIN_SCORE=%d)", market_key, len(scored_all), config.MIN_SCORE)

    if not DRY_RUN:
        for sj in scored_all:
            job_feed.add(market_key, market["label"], sj, now.isoformat())

    # Mark every fetched job (not just ones that scored) as seen, so a
    # low-scoring posting isn't re-evaluated later just because our keyword
    # list changes.
    for j in jobs:
        seen_store.mark_seen(f"{market_key}:{j.dedup_key}", market_key, now.isoformat())

    for sj in scored_all:
        log.info("  score=%-3d %s @ %s (%s)", sj.score, sj.job.title, sj.job.company, sj.job.url)


def main():
    now = store.utcnow()
    seen_store = store.SeenStore(DATA_PATH)
    job_feed = feed.JobFeed()

    for market_key in config.MARKETS:
        try:
            run_market(market_key, seen_store, job_feed, now)
        except Exception:
            log.exception("[%s] run failed", market_key)

    if DRY_RUN:
        log.info("DRY_RUN set — not persisting seen_jobs.json or docs/jobs.json")
    else:
        seen_store.save(now)
        job_feed.save(now)


if __name__ == "__main__":
    main()
