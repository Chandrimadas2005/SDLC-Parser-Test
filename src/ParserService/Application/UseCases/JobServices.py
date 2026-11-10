from dataclasses import dataclass

from ParserService.Domain.Ports.ArtifactStore import ArtifactStore
from ParserService.Domain.Ports.Clock import Clock
from ParserService.Domain.Ports.JobQueue import JobQueue
from ParserService.Domain.Ports.JobRepository import JobRepository


@dataclass(frozen=True, slots=True)
class JobServices:
    """The ports a job use case needs, bundled so constructors stay at three parameters."""

    repository: JobRepository
    store: ArtifactStore
    queue: JobQueue
    clock: Clock
