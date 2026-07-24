from dataclasses import dataclass


@dataclass
class Job:
    source: str
    job_id: str
    title: str
    company: str
    location: str
    date_posted: str
    url: str
    description: str = ""

    @property
    def dedup_key(self) -> str:
        return f"{self.source}:{self.job_id}"
