from dataclasses import dataclass

from ParserService.Domain.Jobs.JobId import JobId
from ParserService.Domain.Jobs.JobStatus import JobStatus


@dataclass(frozen=True, slots=True)
class ParseJobSubmitted:
    """Outcome of a submission: the job to poll, and whether it already existed.

    The same file with the same parser version returns the existing job, so a repeat
    upload is safe (brief, section 2.4).
    """

    job_id: JobId
    status: JobStatus
    already_existed: bool
