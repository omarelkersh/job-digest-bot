import re
from dataclasses import dataclass, field

from . import config

_YEARS_EXPERIENCE_RE = re.compile(
    r"(\d+)\+?\s*(?:years?|jahren?|jahre)\b[^.]{0,25}\b(?:experience|erfahrung)"
    r"|\b(?:experience|erfahrung)\b[^.]{0,25}(\d+)\+?\s*(?:years?|jahren?|jahre)",
    re.IGNORECASE,
)

# "B2"/"C1"/"C2" mentioned near "Deutsch"/"German" — covers phrasings like
# "Deutschkenntnisse mindestens B2", "German C1 required", "Deutsch B2-Niveau".
_GERMAN_LEVEL_RE = re.compile(
    r"\b(?:deutsch\w*|german)\b[^.]{0,20}\b(b2|c1|c2)\b"
    r"|\b(b2|c1|c2)\b[^.]{0,20}\b(?:deutsch\w*|german)\b",
    re.IGNORECASE,
)

# A language from config.OTHER_LANGUAGES mentioned near a fluency/native/
# speaker word — covers "Fluent Dutch required", "native Spanish speaker",
# "Spanish C1". Deliberately narrow level-word list (no generic "required"/
# "essential") to avoid e.g. "polish your skills" false-matching on "Polish".
_LANGUAGE_LEVEL_WORDS = r"(?:native|fluent|proficient|proficiency|mother\s*tongue|speaking|speaker|[bc][12])"
_OTHER_LANGUAGE_RE = re.compile(
    r"\b(" + "|".join(re.escape(l) for l in config.OTHER_LANGUAGES) + r")\b"
    r"[^.]{0,20}\b" + _LANGUAGE_LEVEL_WORDS + r"\b"
    r"|\b" + _LANGUAGE_LEVEL_WORDS + r"\b[^.]{0,20}"
    r"\b(" + "|".join(re.escape(l) for l in config.OTHER_LANGUAGES) + r")\b",
    re.IGNORECASE,
)

# Role/domain keyword groups. A hit in ANY_ROLE gets the big bonus (this is a
# Werkstudent/Praktikum/internship/thesis posting, the core target); a hit in
# ANY_DOMAIN without a role hit gets the smaller bonus (relevant field, but the
# employment type wasn't confirmed by title text alone).
ROLE_KEYWORDS = [
    "werkstudent", "praktikum", "praktikant", "internship", "intern",
    "working student", "abschlussarbeit", "masterarbeit", "thesis",
    "graduate", "junior",
]
DOMAIN_KEYWORDS = [
    "data engineer", "data engineering", "dateningenieur",
    "data scientist", "data science", "machine learning", "ml engineer",
    "mlops", "big data",
]


def _compile(keywords):
    """Word-boundary regexes so short keywords (e.g. 'git', 'lime') don't match
    as substrings inside unrelated words (e.g. 'Digitalisierung', 'sublime')."""
    return [(kw, re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE)) for kw in keywords]


_SKILL_PATTERNS = _compile(config.SKILL_KEYWORDS)
_ROLE_PATTERNS = _compile(ROLE_KEYWORDS)
_DOMAIN_PATTERNS = _compile(DOMAIN_KEYWORDS)
_SENIORITY_PATTERNS = _compile(config.SENIORITY_EXCLUDE)
_LOCATION_PATTERNS = _compile(config.LOCATION_BONUS_KEYWORDS)
_GERMAN_FLUENCY_PATTERNS = _compile(config.GERMAN_FLUENCY_DROP_PATTERNS)
_FULLTIME_EXCLUDE_PATTERNS = _compile(config.FULLTIME_ONLY_TITLE_EXCLUDE)
_VISA_RELOCATION_PATTERNS = _compile(config.VISA_RELOCATION_KEYWORDS)


def _find_all(patterns, text):
    return [kw for kw, pat in patterns if pat.search(text)]


def _find_first(patterns, text):
    for kw, pat in patterns:
        if pat.search(text):
            return kw
    return ""


@dataclass
class ScoredJob:
    job: object
    score: int
    matched_skills: list = field(default_factory=list)
    matched_role: str = ""
    matched_visa: str = ""


def _requires_years_experience(text: str) -> bool:
    for match in _YEARS_EXPERIENCE_RE.finditer(text):
        years = match.group(1) or match.group(2)
        if years and int(years) >= config.EXPERIENCE_MIN_YEARS_TO_DROP:
            return True
    return False


def score_job(job, fulltime_only=False):
    """Return a ScoredJob, or None if the posting should be dropped outright."""
    title_lower = job.title.lower()
    full_text = f"{job.title} {job.description} {job.company}".lower()

    if _find_first(_SENIORITY_PATTERNS, title_lower):
        return None
    if job.description and _requires_years_experience(job.description.lower()):
        return None
    if _find_first(_GERMAN_FLUENCY_PATTERNS, full_text) or _GERMAN_LEVEL_RE.search(full_text):
        return None
    if _OTHER_LANGUAGE_RE.search(full_text):
        return None
    if fulltime_only and _find_first(_FULLTIME_EXCLUDE_PATTERNS, title_lower):
        return None

    matched_skills = _find_all(_SKILL_PATTERNS, full_text)
    skill_score = min(len(matched_skills) * config.SKILL_HIT_WEIGHT, config.SKILL_HIT_CAP)

    matched_role = _find_first(_ROLE_PATTERNS, title_lower)
    matched_domain = _find_first(_DOMAIN_PATTERNS, full_text)

    # A "Werkstudent"/"internship" title alone isn't enough — the search terms
    # are broad enough to surface postings (e.g. general "Digitalisierung"
    # roles) with zero actual data/ML relevance. Require at least one real
    # skill or domain signal before an explicit role-title match counts.
    if not matched_skills and not matched_domain:
        return None

    role_score = 0
    if matched_role:
        role_score = config.ROLE_MATCH_WEIGHT
    elif matched_domain:
        role_score = config.DOMAIN_MATCH_WEIGHT

    location_score = config.LOCATION_BONUS if _find_first(_LOCATION_PATTERNS, full_text) else 0

    matched_visa = _find_first(_VISA_RELOCATION_PATTERNS, full_text)
    visa_score = config.VISA_RELOCATION_BONUS if matched_visa else 0

    total = skill_score + role_score + location_score + visa_score
    if total < config.MIN_SCORE:
        return None

    return ScoredJob(
        job=job,
        score=total,
        matched_skills=matched_skills,
        matched_role=matched_role or matched_domain,
        matched_visa=matched_visa,
    )


def score_and_rank(jobs, fulltime_only=False):
    scored = [score_job(j, fulltime_only=fulltime_only) for j in jobs]
    scored = [s for s in scored if s is not None]
    scored.sort(key=lambda s: s.score, reverse=True)
    return scored
