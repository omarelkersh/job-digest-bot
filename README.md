# Daily Job Digest Bot

Fetches Data Engineering, Data Science, ML Engineering and MLOps postings
once a day, scores them against Omar's CV, and emails four separate
digests:

- **🇪🇺 Europe (Werkstudent)** — Germany only, part-time/student-job focused
  (Bundesagentur für Arbeit + Adzuna). Requires an explicit Werkstudent/
  Praktikum/Internship/Thesis/Working Student/junior title match — a bare
  "Data Engineer" posting with no part-time signal doesn't qualify here
  (it belongs in Europe Full-Time instead).
- **🧳 Europe (Full-Time)** — all of Europe (Adzuna: Germany, Austria,
  Switzerland, Ireland, Netherlands, Spain, France, Italy, Poland, UK, +
  Jooble as an Ireland backup), full-time only, English-language only —
  postings requiring Dutch, Spanish, French, or any other language Omar
  doesn't have are dropped.
- **🏜️ Gulf (Full-Time)** — Saudi Arabia, UAE, Qatar (Jooble — Adzuna
  doesn't operate there), full-time only. Postings mentioning visa
  sponsorship or a relocation package score higher, but it's a bonus, not
  a hard requirement (most professional Gulf hiring of foreign nationals
  comes with visa sponsorship as standard practice even when the listing
  text doesn't say so explicitly).
- **🏠 Remote** — skill-matched remote roles (remote data engineer/
  scientist/ML/etc.) plus lower-barrier "easy to do" tech-adjacent remote
  roles (data annotation, QA testing, technical support), across the same
  countries already used by the other Adzuna-backed markets. A posting must
  actually look remote (mentions "remote"/"home office"/"work from home"/
  etc.) to qualify — a plain title-keyword match on-site doesn't count.

Every market also sorts by proximity to Frankfurt (Omar is based in nearby
Darmstadt) — closer postings are listed first within each email, using real
coordinates when the source provides them (Bundesagentur always does) or a
city-name fallback otherwise. This is purely a display-order tiebreaker —
it never affects whether a posting is included or dropped (that's decided
entirely by MIN_SCORE); a Gulf or Remote posting with unknown distance just
sorts after ones with a known distance, ranked by relevance among themselves.

Runs for free on GitHub Actions, once a day, no server to maintain.

## Job portal

Every job that clears the score threshold (not just the ones capped into an
email) also lands in a browsable portal — search, filter by market/score/
status, sort by distance-to-Frankfurt, track status (New → Shortlisted →
Applied → Interview → Rejected), and generate a tailored CV PDF for any
specific job with one click.

- **Frontend**: `docs/` — static, hosted free on GitHub Pages, reads
  `docs/jobs.json` (written by every digest run).
- **Backend**: `portal_api/` — two Vercel Python functions; one persists
  status changes back to the repo, one calls the Claude API to tailor a CV
  and returns it as a PDF. **This one has real per-use billing** on your
  Anthropic account, unlike everything else in this project. See
  [portal_api/README.md](portal_api/README.md) for full setup (GitHub
  Pages, Vercel, API keys).

## How it works

```
job_digest/
  config.py          skills, role keywords, scoring weights, market definitions
  scoring.py          keyword matching + drop rules (seniority, years-experience,
                        German/other-language requirements, full-time-only gate,
                        remote-required gate, easy-role scoring)
  store.py             data/seen_jobs.json dedup store (market-scoped keys)
  feed.py               docs/jobs.json portal feed (superset of what's emailed)
  emailer.py            Gmail SMTP HTML/plain-text email
  sources/
    arbeitsagentur.py   Bundesagentur für Arbeit Jobsuche API (no signup)
    adzuna.py            Adzuna API (Werkstudent, Europe Full-Time, Remote)
    jooble.py            Jooble API (Gulf, Europe Full-Time backup)
  main.py                orchestrator — run with `python -m job_digest.main`

docs/                  job portal — static, hosted free on GitHub Pages
  index.html / app.js / style.css / config.js
  jobs.json              written by every digest run
  status.json             written by the portal backend

portal_api/            job portal backend — single Vercel Python (Flask) app
                         (real per-use Claude API billing; see its own README)
  app.py                 routes: /api/status, /api/generate_cv
  _shared.py
```

Each run: fetch → dedup against `data/seen_jobs.json` → score → email the
best matches per market → commit the updated dedup file back to the repo.
If a market has zero new matches above the score threshold, no email is
sent for it that day.

Dedup keys are **market-scoped** (`"<market>:<source>:<id>"`) — a posting
already sent in one digest can still legitimately appear in a different
digest (e.g. a remote-tagged Werkstudent posting is relevant to both the
Werkstudent and Remote digests). Only repeats *within the same market* are
suppressed.

### Known limitations

- The Bundesagentur API doesn't return full job description text via
  search, only the title and occupation category — so Werkstudent-market
  scoring (and the German-level / other-language drop rules, which need
  description text) leans much more heavily on title keywords than
  Adzuna/Jooble postings do.
- Adzuna's public support for Ireland (`ie`) isn't confirmed the way the
  other country codes are — if it turns out to be wrong, `adzuna.py` logs
  a warning and skips it rather than failing the run. Jooble queries
  Ireland by location string as a backup regardless, so Ireland coverage
  doesn't depend solely on Adzuna.
- Jooble's free tier defaults to a **500-request cap** (per their signup
  confirmation). The Gulf + Europe Full-Time digests together use roughly
  50 calls/day — comfortably fine if that's a one-time or high-frequency
  reset, but worth watching (Action logs will show HTTP errors from
  `jooble.py` if the quota is hit) if it turns out to be a low-frequency
  cap. Jooble's own signup message says to contact them to raise it.
  The Remote digest deliberately avoids Jooble entirely to not add to this.

## One-time setup

### 1. Adzuna API keys (Werkstudent + Europe Full-Time + Remote digests)

1. Sign up free at https://developer.adzuna.com/
2. Create an app — you'll get an **App ID** and **App Key**.

### 2. Jooble API key (Gulf digest + Europe Full-Time backup)

1. Sign up free at https://jooble.org/api/about
2. You'll get a single API key.

### 3. Gmail App Password (sends all four digests)

1. Turn on 2-Step Verification on the Gmail account you want to send from:
   https://myaccount.google.com/security
2. Generate an App Password: https://myaccount.google.com/apppasswords
   (choose "Mail" / "Other", name it e.g. "job-digest-bot")
3. Copy the 16-character password — you won't see it again.

### 4. Create the GitHub repo and push this code

```bash
cd job-digest-bot
git init
git add .
git commit -m "Initial commit: daily job digest bot"
```

Create an empty repo on GitHub (github.com → New repository, don't
initialize with a README), then:

```bash
git remote add origin https://github.com/<your-username>/<repo-name>.git
git branch -M main
git push -u origin main
```

### 5. Add GitHub Secrets

Repo → **Settings → Secrets and variables → Actions → New repository
secret**. Add each of these:

| Secret name | Value |
|---|---|
| `ADZUNA_APP_ID` | from step 1 |
| `ADZUNA_APP_KEY` | from step 1 |
| `JOOBLE_API_KEY` | from step 2 |
| `GMAIL_ADDRESS` | the Gmail address you generated the app password for |
| `GMAIL_APP_PASSWORD` | the 16-character app password from step 3 |
| `DIGEST_TO_EMAIL` | where the Werkstudent digest should land (e.g. your own inbox) |
| `EUROPE_FULLTIME_DIGEST_TO_EMAIL` | *(optional)* where the Europe Full-Time digest should land — omit to reuse `DIGEST_TO_EMAIL` |
| `GULF_DIGEST_TO_EMAIL` | *(optional)* where the Gulf digest should land — omit to reuse `DIGEST_TO_EMAIL` |
| `REMOTE_DIGEST_TO_EMAIL` | *(optional)* where the Remote digest should land — omit to reuse `DIGEST_TO_EMAIL` |

None of these are ever hardcoded in the repo — the workflow reads them
from `secrets.*` at run time.

### 6. Turn on the Action

Actions are usually enabled by default on push. Go to the repo's
**Actions** tab — you should see "Daily Job Digest". Click into it and
use **Run workflow** to trigger a manual test run before waiting for the
schedule.

The schedule (`.github/workflows/daily-digest.yml`) fires at 05:00 UTC,
which lands at 06:00–07:00 Europe/Berlin depending on daylight saving.

## Local testing

```bash
cp .env.example .env   # fill in values, or export them directly
pip install -r requirements.txt

# Preview matches without sending email or touching the dedup store:
DRY_RUN=1 python -m job_digest.main

# Send for real:
python -m job_digest.main
```

`DRY_RUN=1` logs the subject line and every job that would be sent,
without emailing anything and without marking jobs as seen — safe to
re-run repeatedly while tuning.

## Tuning

All of this lives in `job_digest/config.py`:

- `SKILL_KEYWORDS` — CV skills that earn scoring points
- `EUROPE_ROLE_QUERIES` / `EUROPE_FULLTIME_ROLE_QUERIES` / `GULF_ROLE_QUERIES` /
  `REMOTE_ROLE_QUERIES` — search phrases per market
- `SENIORITY_EXCLUDE` — title keywords that drop a posting outright
- `FULLTIME_ONLY_TITLE_EXCLUDE` — title keywords (Werkstudent, internship,
  part-time, thesis, ...) that drop a posting in the full-time-only markets
  (Europe Full-Time, Gulf, Remote)
- `OTHER_LANGUAGES` — non-English/German/Arabic languages that, when
  required near a fluency/native/speaker word, drop a posting (applies to
  every market — it's never correct to surface a posting requiring
  Dutch/Spanish/French/etc.)
- `VISA_RELOCATION_KEYWORDS` / `VISA_RELOCATION_BONUS` — Gulf scoring bonus
  for postings mentioning visa sponsorship or relocation support
- `EASY_ROLE_KEYWORDS` / `EASY_ROLE_WEIGHT` — lower-barrier tech-adjacent
  titles (data annotation, QA testing, technical support) that qualify a
  posting for the Remote digest even without a strong skill/domain match
- `REMOTE_INDICATOR_KEYWORDS` — required (not just bonus) for the Remote
  market, so a plain "data engineer" search doesn't return on-site roles
- `FRANKFURT_COORDS` — reference point for the real-coordinate distance sort;
  `FRANKFURT_NEAR_CITIES` / `FRANKFURT_MID_CITIES` (+ their `_APPROX_KM`
  values) are the city-name-tier fallback distance estimate for sources
  without coordinates (Jooble)
- `MIN_SCORE` (env `DIGEST_MIN_SCORE`, default 6) — minimum score to include
- `MAX_JOBS_PER_EMAIL` (env `DIGEST_MAX_JOBS_PER_EMAIL`, default 30)
- `ADZUNA_COUNTRIES` (env, default `de`) — Werkstudent-market countries
- `ADZUNA_FULLTIME_COUNTRIES` (env, default `de,at,ch,ie,nl,es,fr,it,pl,gb`) /
  `JOOBLE_FULLTIME_LOCATIONS` (env, default `Ireland`) — Europe Full-Time market
- `GULF_LOCATIONS` (env, default `Saudi Arabia,United Arab Emirates,Qatar`)
- `ADZUNA_REMOTE_COUNTRIES` (env, default: the union of the Werkstudent and
  Europe Full-Time country lists — no new country-support uncertainty)

If a country code turns out to be wrong/unsupported, `adzuna.py` logs a
warning and skips it rather than failing the run — check the Action logs
after your first real run and trim the list if any country consistently
errors.

Postings requiring B2/C1/C2-level or unqualified fluent/native German (or
any of the `OTHER_LANGUAGES`) are **dropped outright**, not flagged — there's
no point seeing a posting that needs a language you don't have.
