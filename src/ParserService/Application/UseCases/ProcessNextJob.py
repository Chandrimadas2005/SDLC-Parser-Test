from ParserService.Application.UseCases.ArtifactKeys import ArtifactKeys
from ParserService.Application.UseCases.JobServices import JobServices
from ParserService.Domain.Jobs.Job import Job
from ParserService.Domain.Jobs.JobCompletion import JobCompletion
from ParserService.Domain.Jobs.JobStatus import JobStatus
from ParserService.Domain.Ports.DocumentParser import DocumentParser


class ProcessNextJob:
    """Take the next queued job, parse its file in isolation and record the result.

    The result file is written before the job record is updated, so a stop in
    between only means the next attempt overwrites the file (brief, section 2.7).
    """

    def __init__(self, services: JobServices, parser: DocumentParser, keys: ArtifactKeys) -> None:
        self._services = services
        self._parser = parser
        self._keys = keys

    def execute(self) -> bool:
        """Process one job if one is waiting.

        Returns:
            ``True`` when a job was taken from the queue, ``False`` when it was empty.
        """
        job_id = self._services.queue.claim()
        if job_id is None:
            return False
        job = self._services.repository.get(job_id)
        if job is not None:
            self._process(self._running(job))
        return True

    def _running(self, job: Job) -> Job:
        if job.status is JobStatus.RUNNING:
            return job
        return job.start(self._services.clock.now())

    def _process(self, job: Job) -> None:
        parsed = self._parser.parse(job.file_pointer, job.file_name)
        if parsed.is_err:
            failed = job.fail(parsed.unwrap_err(), self._services.clock.now())
            self._services.repository.update(failed)
            return
        outcome = parsed.unwrap()
        pointer = self._keys.result_json(job.key.file_hash, job.key.parser_version)
        self._services.store.put(pointer, outcome.content)
        completion = JobCompletion(JobStatus(outcome.status.value), pointer, outcome.warning_count)
        self._services.repository.update(job.complete(completion, self._services.clock.now()))
