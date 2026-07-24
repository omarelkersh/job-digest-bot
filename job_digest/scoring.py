import re
from dataclasses import dataclass, field

from . import config

_YEARS_EXPERIENCE_RE = re.compile(
    r"(\d+)\+?\s*(?:years?|jahren?|jahre)\b[^.]{0,25}\b(?:experience|erfahrung)"
    r"|\b(?:experience|erfahrung)\b[^.]{0,25}(\d+)\+?\s*(?:years?|jahren?|jahre)",
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
_GERMAN_FLUENCY_PATTERNS = _compile(config.GERMAN_FLUENCY_PATTERNS)


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
    german_required: bool = False


def _requires_years_experience(text: str) -> bool:
    for match in _YEARS_EXPERIENCE_RE.finditer(text):
        years = match.group(1) or match.group(2)
        if years and int(years) >= config.EXPERIENCE_MIN_YEARS_TO_DROP:
            return True
    return False


def score_job(job):
    """Return a ScoredJob, or None if the posting should be dropped outright."""
    title_lower = job.title.lower()
    full_text = f"{job.title} {job.description} {job.company}".lower()

    if _find_first(_SENIORITY_PATTERNS, title_lower):
        return None
    if job.description and _requires_years_experience(job.description.lower()):
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

    total = skill_score + role_score + location_score
    if total < config.MIN_SCORE:
        return None

    german_required = bool(_find_first(_GERMAN_FLUENCY_PATTERNS, full_text))

    return ScoredJob(
        job=job,
        score=total,
        matched_skills=matched_skills,
        matched_role=matched_role or matched_domain,
        german_required=german_required,
    )


def score_and_rank(jobs):
    scored = [score_job(j) for j in jobs]
    scored = [s for s in scored if s is not None]
    scored.sort(key=lambda s: s.score, reverse=True)
    return scored
