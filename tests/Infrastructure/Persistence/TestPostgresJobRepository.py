from dataclasses import replace
from pathlib import Path

from sqlalchemy.engine import Engine

from ParserService.Domain.Errors import JobRepositoryError
from ParserService.Domain.Jobs import (
    ArtifactPointer,
    FailureReason,
    FileHash,
    FileName,
    Instant,
    Job,
    JobCompletion,
    JobId,
    JobKey,
    JobStatus,
    ParserVersion,
)
from ParserService.Infrastructure.Persistence import (
    DatabaseEngineFactory,
    JobRecordMapper,
    PostgresJobRepository,
)

JOB = Job(
    id=JobId("00000000-0000-4000-8000-000000000010"),
    key=JobKey(FileHash("d" * 64), ParserVersion("0.1.0")),
    file_name=FileName("report.pdf"),
    file_pointer=ArtifactPointer("files/dd/original.pdf"),
    created_at=Instant(10_000),
)


class TestPostgresJobRepository:
    """Records round-trip exactly, the key is unique, and expected failures are Results."""

    @staticmethod
    def _repository(engine: Engine) -> PostgresJobRepository:
        return PostgresJobRepository(engine, JobRecordMapper())

    def test_add_then_get_returns_an_equal_job(self, engine: Engine) -> None:
        repository = self._repository(engine)

        assert repository.add(JOB).unwrap() == JOB
        assert repository.get(JOB.id) == JOB
        assert repository.find_by_key(JOB.key) == JOB

    def test_unknown_ids_and_keys_return_none(self, engine: Engine) -> None:
        repository = self._repository(engine)

        assert repository.get(JobId.new()) is None
        assert repository.find_by_key(JobKey(FileHash("e" * 64), ParserVersion("9"))) is None

    def test_same_file_hash_and_parser_version_is_rejected_as_duplicate(
        self, engine: Engine
    ) -> None:
        repository = self._repository(engine)
        repository.add(JOB)
        clone = replace(JOB, id=JobId.new(), file_name=FileName("other-name.pdf"))

        assert repository.add(clone).unwrap_err() is JobRepositoryError.DUPLICATE_KEY
        assert repository.get(clone.id) is None

    def test_same_file_hash_with_another_parser_version_is_a_new_job(self, engine: Engine) -> None:
        repository = self._repository(engine)
        repository.add(JOB)
        newer = replace(
            JOB, id=JobId.new(), key=replace(JOB.key, parser_version=ParserVersion("0.2.0"))
        )

        assert repository.add(newer).is_ok

    def test_update_persists_every_transition_field(self, engine: Engine) -> None:
        repository = self._repository(engine)
        repository.add(JOB)
        completion = JobCompletion(JobStatus.PARTIAL, ArtifactPointer("results/dd/result.json"), 4)
        finished = JOB.start(Instant(11_000)).complete(completion, Instant(12_500))

        assert repository.update(finished).is_ok
        stored = repository.get(JOB.id)

        assert stored == finished
        assert stored is not None
        assert stored.duration is not None
        assert stored.duration.milliseconds == 1_500

    def test_failed_job_round_trips_its_reason(self, engine: Engine) -> None:
        repository = self._repository(engine)
        repository.add(JOB)
        failed = JOB.start(Instant(11_000)).fail(FailureReason.PASSWORD_PROTECTED, Instant(11_010))

        repository.update(failed)

        assert repository.get(JOB.id) == failed

    def test_update_of_a_missing_job_is_not_found(self, engine: Engine) -> None:
        repository = self._repository(engine)

        assert repository.update(JOB).unwrap_err() is JobRepositoryError.NOT_FOUND

    def test_delete_removes_the_record_once(self, engine: Engine) -> None:
        repository = self._repository(engine)
        repository.add(JOB)

        assert repository.delete(JOB.id)
        assert not repository.delete(JOB.id)
        assert repository.get(JOB.id) is None

    def test_unreachable_database_is_reported_not_raised(self, tmp_path: Path) -> None:
        engine = DatabaseEngineFactory().create(f"sqlite:///{tmp_path.as_posix()}")
        repository = self._repository(engine)

        assert repository.add(JOB).unwrap_err() is JobRepositoryError.STORE_UNAVAILABLE
        assert repository.update(JOB).unwrap_err() is JobRepositoryError.STORE_UNAVAILABLE
