"""Local JSON store of job IDs already emailed, so re-runs never duplicate a
posting. Committed back to the repo by the GitHub Actions workflow after
every run, so it persists indefinitely without any external service.
"""
import json
import os
from datetime import datetime, timedelta, timezone

RETENTION_DAYS = 180

# Keys used to be bare "source:id" (e.g. "arbeitsagentur:12345"), shared across
# every market — meaning a job already sent in one digest would silently never
# appear in another digest's email even though it's relevant there too. Keys
# are now market-scoped ("europe:arbeitsagentur:12345"). Every key ever
# written under the old scheme came from the "europe" market (the only one
# that had run before this split), so migrate legacy bare keys by prefixing
# "europe:" rather than losing the history and resending everything once.
_LEGACY_SOURCE_PREFIXES = ("arbeitsagentur:", "adzuna:", "jooble:")


class SeenStore:
    def __init__(self, path):
        self.path = path
        self._data = self._load()

    def _load(self):
        if not os.path.exists(self.path):
            return {}
        with open(self.path, "r", encoding="utf-8") as f:
            try:
                raw = json.load(f)
            except json.JSONDecodeError:
                return {}
        migrated = {}
        for key, meta in raw.items():
            if key.startswith(_LEGACY_SOURCE_PREFIXES):
                key = f"europe:{key}"
            migrated[key] = meta
        return migrated

    def is_new(self, key):
        return key not in self._data

    def mark_seen(self, key, market, now_iso):
        self._data[key] = {"first_seen": now_iso, "market": market}

    def save(self, now):
        cutoff = now - timedelta(days=RETENTION_DAYS)
        pruned = {}
        for key, meta in self._data.items():
            try:
                seen_at = datetime.fromisoformat(meta["first_seen"])
            except (KeyError, ValueError):
                pruned[key] = meta
                continue
            if seen_at >= cutoff:
                pruned[key] = meta
        self._data = pruned

        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, sort_keys=True)
            f.write("\n")


def utcnow():
    return datetime.now(timezone.utc)
