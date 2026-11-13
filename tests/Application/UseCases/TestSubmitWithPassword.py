from ParserService.Application.Dto import SubmitParseJobCommand
from ParserService.Application.UseCases import (
    ArtifactKeys,
    JobServices,
    SubmitParseJob,
    SubmitPolicy,
)
from ParserService.Domain.Jobs import (
    FailureReason,
    FileHash,
    FileName,
    Instant,
    JobStatus,
    ParserVersion,
)
from tests.Fakes import FixedClock, InMemoryArtifactStore, InMemoryJobQueue, InMemoryJobRepository

CONTENT = b"%PDF-1.4 synthetic locked file"
SECRET = "synthetic-secret"


class TestSubmitWithPassword:
    """A password travels with the file, and unlocks a file that failed for want of one."""

    @staticmethod
    def _submit() -> tuple[SubmitParseJob, JobServices]:
        services = JobServices(
            InMemoryJobRepository(),
            InMemoryArtifactStore(),
            InMemoryJobQueue(5),
            FixedClock(Instant(1)),
        )
        policy = SubmitPolicy(ParserVersion("0.1.0"), 1_000)
        return SubmitParseJob(services, policy, ArtifactKeys()), services

    @staticmethod
    def _stored_password(services: JobServices) -> bytes | None:
        return services.store.read(ArtifactKeys().password(FileHash.of(CONTENT)))

    def test_a_new_file_keeps_its_password_for_the_worker(self) -> None:
        submit, services = self._submit()

        submit.execute(SubmitParseJobCommand(FileName("a.pdf"), CONTENT, SECRET))

        assert self._stored_password(services) == SECRET.encode()

    def test_a_locked_job_is_parsed_again_once_a_password_arrives(self) -> None:
        submit, services = self._submit()
        first = submit.execute(SubmitParseJobCommand(FileName("a.pdf"), CONTENT)).unwrap()
        job = services.repository.get(first.job_id)
        assert job is not None
        locked = job.start(Instant(2)).fail(FailureReason.PASSWORD_PROTECTED, Instant(3))
        services.repository.update(locked)

        again = submit.execute(SubmitParseJobCommand(FileName("a.pdf"), CONTENT, SECRET))

        assert again.unwrap().status is JobStatus.QUEUED
        assert again.unwrap().already_existed is False
        assert self._stored_password(services) == SECRET.encode()

    def test_a_password_does_not_reopen_other_jobs(self) -> None:
        submit, services = self._submit()
        submit.execute(SubmitParseJobCommand(FileName("a.pdf"), CONTENT))

        again = submit.execute(SubmitParseJobCommand(FileName("a.pdf"), CONTENT, SECRET))

        assert again.unwrap().already_existed is True
        assert self._stored_password(services) is None
        assert "synthetic-secret" not in repr(
            SubmitParseJobCommand(FileName("a"), b"", "synthetic-secret")
        )
