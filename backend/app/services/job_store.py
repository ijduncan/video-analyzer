from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Job:
    job_id: str
    file_id: str  # Google File API name
    file_uri: str  # Google File API URI
    mime_type: str
    filename: str
    size_bytes: int
    local_path: str
    youtube_url: str | None = None
    status: str = "ready"  # ready, analyzing, complete, error
    current_pass: int | None = None
    current_scene: int | None = None
    total_scenes: int | None = None
    flash_result: dict | None = None
    deep_results: list[dict] = field(default_factory=list)
    summary: dict | None = None
    cost_estimate: dict | None = None
    custom_prompt: str | None = None
    custom_result: dict | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# In-memory store
_jobs: dict[str, Job] = {}


def create_job(job: Job) -> Job:
    _jobs[job.job_id] = job
    return job


def get_job(job_id: str) -> Job | None:
    return _jobs.get(job_id)


def update_job(job_id: str, **kwargs) -> Job | None:
    job = _jobs.get(job_id)
    if job is None:
        return None
    for key, value in kwargs.items():
        setattr(job, key, value)
    return job


def delete_job(job_id: str) -> bool:
    return _jobs.pop(job_id, None) is not None
