"""Profile, keyword, and market configuration derived from Omar's CV.

Tune thresholds/keywords here — nothing else in the codebase should need editing
for day-to-day adjustments.
"""
import os

# ---------------------------------------------------------------------------
# Skill keywords (from CV) — each hit in a job's title/description adds points
# ---------------------------------------------------------------------------
SKILL_KEYWORDS = [
    # Languages
    "python", "sql", "rust",
    # Big data
    "spark", "pyspark", "hadoop", "hive", "sqoop", "airflow", "etl", "big data",
    "kafka", "databricks",
    # ML
    "scikit-learn", "sklearn", "tensorflow", "pytorch", "shap", "lime",
    "computer vision", "llm", "large language model", "nlp", "machine learning",
    "deep learning",
    # Cloud / DevOps
    "aws", "docker", "git", "kubernetes", "ci/cd",
    # Databases
    "snowflake", "postgresql", "postgres", "mongodb", "nosql",
]

# ---------------------------------------------------------------------------
# Seniority guardrails — title hits here drop the posting outright
# ---------------------------------------------------------------------------
SENIORITY_EXCLUDE = [
    "senior", "sr.", "lead ", "principal", "staff engineer", "head of",
    "director", "manager", "vp ", "chief", "berufserfahrung erforderlich",
]

# Regex-detected "N+ years experience" style requirements (English + German).
# Matched against full description text where available (Adzuna, Jooble).
EXPERIENCE_MIN_YEARS_TO_DROP = 3

# German-fluency phrases — a match here drops the posting outright (B2/C1/C2
# level or unqualified native/fluent wording, which in practice means C1+).
# B2/C1/C2 mentioned near "deutsch"/"german" is caught separately by a regex
# in scoring.py; this list is for qualitative phrasing that doesn't name a
# level explicitly.
GERMAN_FLUENCY_DROP_PATTERNS = [
    "verhandlungssicheres deutsch", "verhandlungssicher in deutsch",
    "fließende deutschkenntnisse", "muttersprachliches deutsch",
    "fluent german", "native german",
]

# Languages (besides English/Arabic, which Omar has, and German — handled
# separately above at the A2-appropriate B2+ threshold) that a posting might
# require. A match near a fluency/native/speaker word drops the posting —
# used for the Ireland/Netherlands/Spain full-time market, where local-language
# requirements (Dutch, Spanish, French, etc.) are common on some listings.
OTHER_LANGUAGES = [
    "dutch", "nederlands", "spanish", "español", "french", "français",
    "portuguese", "português", "italian", "italiano", "polish", "polski",
    "swedish", "danish", "norwegian", "finnish",
]

# Title keywords that disqualify a posting from a "full-time only" market
# (Gulf, Europe Full-Time) — these markets should never surface Werkstudent/
# internship/part-time postings.
FULLTIME_ONLY_TITLE_EXCLUDE = [
    "werkstudent", "praktikum", "praktikant", "internship", "intern",
    "working student", "part-time", "part time", "teilzeit",
    "thesis", "abschlussarbeit", "masterarbeit",
]

# Mentioning visa sponsorship / relocation support is a strong positive signal
# for the Gulf market, but not a hard requirement — most professional hires of
# foreign nationals in the Gulf come with visa sponsorship as standard practice
# even when the listing text doesn't spell it out, so requiring the phrase
# would hide too many genuine matches. It only adds bonus points when present.
VISA_RELOCATION_KEYWORDS = [
    "visa sponsorship", "visa sponsored", "sponsorship provided",
    "relocation package", "relocation assistance", "relocation support",
    "work permit provided", "expat package", "expatriate package",
]
VISA_RELOCATION_BONUS = 4

# "Easy to do" remote roles — still data/tech-adjacent, but lower-barrier than
# a full Data Engineer/Scientist/ML title, so they wouldn't otherwise clear
# the skill/domain-match gate in score_job(). Only used when a market opts in
# via allow_easy_roles (currently just "remote").
EASY_ROLE_KEYWORDS = [
    "data annotation", "data labeling", "data labelling", "data entry",
    "qa tester", "quality assurance tester", "quality assurance analyst",
    "technical support", "it support",
]
EASY_ROLE_WEIGHT = 6

# Indicates a posting is actually remote — required (not just bonus-scored)
# for the "remote" market, since a plain "data engineer" search returns plenty
# of on-site roles too.
REMOTE_INDICATOR_KEYWORDS = [
    "remote", "home office", "homeoffice", "work from home", "anywhere",
    "distributed team",
]

# Proximity to Frankfurt (Omar is based in Darmstadt, ~30km away) — purely a
# SORT key (closer listed first within an email), never a factor in whether a
# posting is included or dropped; that's decided by MIN_SCORE alone. Uses
# real coordinates when the source provides them (Bundesagentur always does;
# Adzuna sometimes does); falls back to a coarse city-name-tier distance
# estimate when no coordinates are available (Jooble never provides them).
FRANKFURT_COORDS = (50.1109, 8.6821)
FRANKFURT_NEAR_CITIES = [
    "frankfurt", "darmstadt", "wiesbaden", "mainz", "offenbach",
    "rhein-main", "rüsselsheim", "hanau",
]
FRANKFURT_MID_CITIES = [
    "mannheim", "kassel", "gießen", "giessen", "koblenz",
    "würzburg", "wuerzburg", "heidelberg", "aschaffenburg",
]
FRANKFURT_NEAR_APPROX_KM = 20   # approximate distance estimate for the near-city tier
FRANKFURT_MID_APPROX_KM = 120   # approximate distance estimate for the mid-city tier

# ---------------------------------------------------------------------------
# Scoring weights
# ---------------------------------------------------------------------------
SKILL_HIT_WEIGHT = 2
SKILL_HIT_CAP = 20          # max points contributable by skill keyword hits
ROLE_MATCH_WEIGHT = 8       # explicit Werkstudent/Praktikum/Internship/Thesis hit
DOMAIN_MATCH_WEIGHT = 5     # Data Engineer/Scientist/ML/MLOps hit without a role hit
LOCATION_BONUS = 2          # Darmstadt / remote mentioned
MIN_SCORE = int(os.environ.get("DIGEST_MIN_SCORE", "6"))

LOCATION_BONUS_KEYWORDS = ["darmstadt", "remote", "home office", "homeoffice"]

# ---------------------------------------------------------------------------
# Market definitions
# ---------------------------------------------------------------------------
# "Europe" market: Germany (Bundesagentur) + Adzuna across the German-speaking
# labour market, where "Werkstudent"/"Praktikum"/"Abschlussarbeit" are real,
# distinct employment categories. Part-time/student-job focused.
EUROPE_ROLE_QUERIES = [
    "Werkstudent Data Engineering",
    "Werkstudent Data Science",
    "Werkstudent Machine Learning",
    "Werkstudent MLOps",
    "Werkstudent Big Data",
    "Praktikum Data Engineering",
    "Praktikum Machine Learning",
    "Abschlussarbeit Data Science",
    "working student data engineer",
    "working student data scientist",
    "working student machine learning",
    "internship data engineer",
    "internship machine learning",
    "remote data engineer python",
]

# Germany only — the part-time/Werkstudent digest is strictly Germany now.
ADZUNA_EUROPE_COUNTRIES = os.environ.get("ADZUNA_COUNTRIES", "de").split(",")

# "Europe Full-Time" market: full-time roles across all of Europe (including
# Germany — a German full-time posting won't double up with the part-time
# digest because that market requires an explicit Werkstudent/Praktikum/
# thesis role-title match now, see require_role_match below). Adzuna's public
# support for "ie" (Ireland) isn't confirmed the way the others are
# (adzuna.py skips/warns rather than fails if it's wrong), so Jooble queries
# Ireland by location string as a redundant backup.
EUROPE_FULLTIME_ROLE_QUERIES = [
    "data engineer",
    "data scientist",
    "machine learning engineer",
    "mlops engineer",
    "junior data engineer",
    "junior data scientist",
    "graduate data engineer",
    "graduate machine learning engineer",
    "entry level data engineer",
]

ADZUNA_FULLTIME_COUNTRIES = os.environ.get(
    "ADZUNA_FULLTIME_COUNTRIES", "de,at,ch,ie,nl,es,fr,it,pl,gb"
).split(",")
# Jooble backup kept to just Ireland (the one genuinely uncertain Adzuna code)
# rather than broadened to match — Gulf + this backup already use a
# meaningful share of Jooble's default 500-request quota.
JOOBLE_FULLTIME_LOCATIONS = os.environ.get("JOOBLE_FULLTIME_LOCATIONS", "Ireland").split(",")

# "Gulf" market: full-time only, via Jooble (Adzuna does not operate there).
GULF_ROLE_QUERIES = [
    "data engineer",
    "data scientist",
    "machine learning engineer",
    "mlops engineer",
    "junior data engineer",
    "junior data scientist",
    "data engineer visa sponsorship",
    "data scientist relocation",
]

GULF_LOCATIONS = os.environ.get(
    "GULF_LOCATIONS", "Saudi Arabia,United Arab Emirates,Qatar"
).split(",")

# "Remote" market: skill-matched roles ("remote data engineer", "remote python
# developer", ...) plus lower-barrier "easy to do" tech-adjacent roles (data
# annotation, QA testing, technical support). Reuses the Adzuna countries
# already configured above rather than adding new ones — no new coverage
# uncertainty, and Jooble is deliberately NOT used here since the Gulf +
# Europe Full-Time digests already use a meaningful share of Jooble's default
# 500-request quota.
REMOTE_ROLE_QUERIES = [
    "remote data engineer",
    "remote data scientist",
    "remote machine learning engineer",
    "remote data analyst",
    "remote python developer",
    "remote sql developer",
    "remote junior data",
    "remote data annotation",
    "remote qa tester",
    "remote technical support",
]

ADZUNA_REMOTE_COUNTRIES = (
    os.environ.get("ADZUNA_REMOTE_COUNTRIES").split(",")
    if os.environ.get("ADZUNA_REMOTE_COUNTRIES")
    else list(dict.fromkeys(ADZUNA_EUROPE_COUNTRIES + ADZUNA_FULLTIME_COUNTRIES))
)

# Note: the "requires a language Omar doesn't have" check (OTHER_LANGUAGES,
# in scoring.py) applies globally to every market, not just Europe Full-Time —
# it's never correct to surface a posting requiring Dutch/Spanish/French/etc.
# regardless of which digest it'd land in.
MARKETS = {
    "europe": {
        "label": "Europe (Werkstudent)",
        "role_queries": EUROPE_ROLE_QUERIES,
        "fulltime_only": False,
        "require_role_match": True,
    },
    "europe_fulltime": {
        "label": "Europe (Full-Time)",
        "role_queries": EUROPE_FULLTIME_ROLE_QUERIES,
        "fulltime_only": True,
    },
    "gulf": {
        "label": "Gulf (Full-Time)",
        "role_queries": GULF_ROLE_QUERIES,
        "fulltime_only": True,
    },
    "remote": {
        "label": "Remote",
        "role_queries": REMOTE_ROLE_QUERIES,
        "fulltime_only": True,
        "require_remote": True,
        "allow_easy_roles": True,
    },
}
