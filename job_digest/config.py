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

# German-fluency phrases — postings matching these are kept but flagged, not dropped.
GERMAN_FLUENCY_PATTERNS = [
    "verhandlungssicheres deutsch", "verhandlungssicher in deutsch",
    "fließende deutschkenntnisse", "muttersprachliches deutsch",
    "deutsch c1", "deutsch c2", "deutschkenntnisse c1", "deutschkenntnisse c2",
    "fluent german", "native german", "german c1", "german c2",
]

# ---------------------------------------------------------------------------
# Scoring weights
# ---------------------------------------------------------------------------
SKILL_HIT_WEIGHT = 2
SKILL_HIT_CAP = 20          # max points contributable by skill keyword hits
ROLE_MATCH_WEIGHT = 8       # explicit Werkstudent/Praktikum/Internship/Thesis hit
DOMAIN_MATCH_WEIGHT = 5     # Data Engineer/Scientist/ML/MLOps hit without a role hit
LOCATION_BONUS = 2          # Darmstadt / remote mentioned
MIN_SCORE = int(os.environ.get("DIGEST_MIN_SCORE", "6"))
MAX_JOBS_PER_EMAIL = int(os.environ.get("DIGEST_MAX_JOBS_PER_EMAIL", "30"))

LOCATION_BONUS_KEYWORDS = ["darmstadt", "remote", "home office", "homeoffice"]

# ---------------------------------------------------------------------------
# Market definitions
# ---------------------------------------------------------------------------
# "Europe" market: Germany (Bundesagentur) + Adzuna across Germany + neighbouring
# European countries. Role queries include German-language Werkstudent/Praktikum/
# Abschlussarbeit terms since these are Germany-specific employment categories.
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

# Countries Adzuna's public API is confirmed/commonly documented to support in
# Europe. If a code is wrong or later deprecated, adzuna.py logs a warning and
# skips it rather than failing the whole run — adjust this list freely.
ADZUNA_EUROPE_COUNTRIES = os.environ.get(
    "ADZUNA_COUNTRIES", "de,at,nl,fr,it,es,pl,gb,ch"
).split(",")

# "Gulf" market: no Werkstudent-equivalent status exists here, so queries lean
# on internship/graduate/junior framing instead of the German-specific terms.
GULF_ROLE_QUERIES = [
    "data engineer internship",
    "data scientist internship",
    "junior data engineer",
    "junior data scientist",
    "graduate machine learning engineer",
    "mlops engineer",
    "data engineer",
    "machine learning engineer",
]

GULF_LOCATIONS = os.environ.get(
    "GULF_LOCATIONS", "Saudi Arabia,United Arab Emirates,Qatar"
).split(",")

MARKETS = {
    "europe": {
        "label": "Europe",
        "subject_emoji": "\U0001F1EA\U0001F1FA",  # EU flag
        "recipient_env": "DIGEST_TO_EMAIL",
        "role_queries": EUROPE_ROLE_QUERIES,
    },
    "gulf": {
        "label": "Gulf",
        "subject_emoji": "\U0001F3DC️",  # desert
        "recipient_env": "GULF_DIGEST_TO_EMAIL",
        "role_queries": GULF_ROLE_QUERIES,
    },
}
