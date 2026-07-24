# Daily Job Digest Bot

Fetches Werkstudent / internship / thesis-combo / junior Data Engineering,
Data Science, ML Engineering and MLOps postings once a day, scores them
against Omar's CV, and emails two separate digests:

- **🇪🇺 Europe** — Germany (Bundesagentur für Arbeit) + Germany/Austria/
  Netherlands/France/Italy/Spain/Poland/UK/Switzerland (Adzuna)
- **🏜️ Gulf** — Saudi Arabia, UAE, Qatar (Jooble — Adzuna doesn't cover
  the Gulf)

Runs for free on GitHub Actions, once a day, no server to maintain.

## How it works

```
job_digest/
  config.py          skills, role keywords, scoring weights, market definitions
  scoring.py          keyword matching + drop rules (seniority, years-experience)
  store.py             data/seen_jobs.json dedup store
  emailer.py            Gmail SMTP HTML/plain-text email
  sources/
    arbeitsagentur.py   Bundesagentur für Arbeit Jobsuche API (no signup)
    adzuna.py            Adzuna API (Europe)
    jooble.py            Jooble API (Gulf)
  main.py                orchestrator — run with `python -m job_digest.main`
```

Each run: fetch → dedup against `data/seen_jobs.json` → score → email the
best matches per market → commit the updated dedup file back to the repo.
If a market has zero new matches above the score threshold, no email is
sent for it that day.

### Known limitation

The Bundesagentur API doesn't return full job description text via search,
only the title and occupation category — so German-market scoring leans
more heavily on title keywords than Adzuna/Jooble postings do, which
include a description snippet.

## One-time setup

### 1. Adzuna API keys (Europe digest)

1. Sign up free at https://developer.adzuna.com/
2. Create an app — you'll get an **App ID** and **App Key**.

### 2. Jooble API key (Gulf digest)

1. Sign up free at https://jooble.org/api/about
2. You'll get a single API key.

### 3. Gmail App Password (sends both digests)

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
| `DIGEST_TO_EMAIL` | where the Europe digest should land (e.g. your own inbox) |
| `GULF_DIGEST_TO_EMAIL` | *(optional)* where the Gulf digest should land — omit to reuse `DIGEST_TO_EMAIL` |

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
- `EUROPE_ROLE_QUERIES` / `GULF_ROLE_QUERIES` — search phrases per market
- `SENIORITY_EXCLUDE` — title keywords that drop a posting outright
- `MIN_SCORE` (env `DIGEST_MIN_SCORE`, default 6) — minimum score to include
- `MAX_JOBS_PER_EMAIL` (env `DIGEST_MAX_JOBS_PER_EMAIL`, default 30)
- `ADZUNA_COUNTRIES` (env, default `de,at,nl,fr,it,es,pl,gb,ch`) — Adzuna
  country codes queried for the Europe digest. If a code turns out to be
  wrong/unsupported, `adzuna.py` logs a warning and skips it rather than
  failing the run — check the Action logs after your first real run and
  trim the list if any country consistently errors.
- `GULF_LOCATIONS` (env, default `Saudi Arabia,United Arab Emirates,Qatar`)

Postings requiring fluent/native German are **kept, not dropped** — they
get a "⚠️ may require fluent German" note in the email so you can judge
case by case.
