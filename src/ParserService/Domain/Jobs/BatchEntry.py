from dataclasses import dataclass

from ParserService.Domain.Jobs.FileName import FileName
from ParserService.Domain.Jobs.JobId import JobId


@dataclass(frozen=True, slots=True)
class BatchEntry:
    """One file of a multi-file upload and the job that parses it."""

    file_name: FileName
    job_id: JobId
