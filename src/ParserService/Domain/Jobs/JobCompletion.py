from dataclasses import dataclass

from ParserService.Domain.Jobs.ArtifactPointer import ArtifactPointer
from ParserService.Domain.Jobs.JobStatus import JobStatus


@dataclass(frozen=True, slots=True)
class JobCompletion:
    """What a finished parse hands back to the job: its result and how good it is."""

    status: JobStatus
    result_pointer: ArtifactPointer
    warning_count: int

    def __post_init__(self) -> None:
        if self.status not in (JobStatus.SUCCEEDED, JobStatus.PARTIAL):
            message = "a completion is either succeeded or partial"
            raise ValueError(message)
        if self.warning_count < 0:
            message = "warning count cannot be negative"
            raise ValueError(message)
