from sqlalchemy.engine import RowMapping

from ParserService.Domain.Jobs.ArtifactPointer import ArtifactPointer
from ParserService.Domain.Jobs.Duration import Duration
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Domain.Jobs.FileHash import FileHash
from ParserService.Domain.Jobs.FileName import FileName
from ParserService.Domain.Jobs.Instant import Instant
from ParserService.Domain.Jobs.Job import Job
from ParserService.Domain.Jobs.JobId import JobId
from ParserService.Domain.Jobs.JobKey import JobKey
from ParserService.Domain.Jobs.JobStatus import JobStatus
from ParserService.Domain.Jobs.ParserVersion import ParserVersion
from ParserService.Infrastructure.Persistence.JobColumn import JobColumn


class JobRecordMapper:
    """Translates between ``Job`` value objects and flat database rows."""

    def to_row(self, job: Job) -> dict[str, object]:
        """Flatten a job into column values.

        Args:
            job: The job to store.

        Returns:
            Column name to value, ready for an insert or update.
        """
        return {
            JobColumn.ID: job.id.value,
            JobColumn.FILE_HASH: job.key.file_hash.value,
            JobColumn.PARSER_VERSION: job.key.parser_version.value,
            JobColumn.FILE_NAME: job.file_name.value,
            JobColumn.STATUS: job.status.value,
            JobColumn.FAILURE_REASON: self._enum_value(job.failure_reason),
            JobColumn.ATTEMPT_COUNT: job.attempt_count,
            JobColumn.FILE_POINTER: job.file_pointer.key,
            JobColumn.RESULT_POINTER: self._pointer_value(job.result_pointer),
            JobColumn.WARNING_COUNT: job.warning_count,
            JobColumn.CREATED_AT: job.created_at.epoch_ms,
            JobColumn.STARTED_AT: self._instant_value(job.started_at),
            JobColumn.FINISHED_AT: self._instant_value(job.finished_at),
            JobColumn.DURATION_MS: job.duration.milliseconds if job.duration else None,
        }

    def from_row(self, row: RowMapping) -> Job:
        """Rebuild a job from column values.

        Args:
            row: A row mapping as returned by SQLAlchemy.

        Returns:
            The job the row describes.
        """
        return Job(
            id=JobId(str(row[JobColumn.ID])),
            key=self._key(row),
            file_name=FileName(str(row[JobColumn.FILE_NAME])),
            file_pointer=ArtifactPointer(str(row[JobColumn.FILE_POINTER])),
            created_at=Instant(self._int(row[JobColumn.CREATED_AT])),
            status=JobStatus(str(row[JobColumn.STATUS])),
            failure_reason=self._reason(row[JobColumn.FAILURE_REASON]),
            attempt_count=self._int(row[JobColumn.ATTEMPT_COUNT]),
            result_pointer=self._pointer(row[JobColumn.RESULT_POINTER]),
            warning_count=self._int(row[JobColumn.WARNING_COUNT]),
            started_at=self._instant(row[JobColumn.STARTED_AT]),
            finished_at=self._instant(row[JobColumn.FINISHED_AT]),
            duration=self._duration(row[JobColumn.DURATION_MS]),
        )

    @staticmethod
    def _key(row: RowMapping) -> JobKey:
        return JobKey(
            FileHash(str(row[JobColumn.FILE_HASH])),
            ParserVersion(str(row[JobColumn.PARSER_VERSION])),
        )

    @staticmethod
    def _reason(value: object) -> FailureReason | None:
        return FailureReason(str(value)) if value is not None else None

    @classmethod
    def _duration(cls, value: object) -> Duration | None:
        return Duration(cls._int(value)) if value is not None else None

    @staticmethod
    def _int(value: object) -> int:
        if not isinstance(value, int):
            message = f"expected an integer column value, got {type(value).__name__}"
            raise TypeError(message)
        return value

    @staticmethod
    def _enum_value(value: FailureReason | None) -> str | None:
        return value.value if value is not None else None

    @staticmethod
    def _pointer_value(pointer: ArtifactPointer | None) -> str | None:
        return pointer.key if pointer is not None else None

    @staticmethod
    def _instant_value(instant: Instant | None) -> int | None:
        return instant.epoch_ms if instant is not None else None

    @classmethod
    def _instant(cls, value: object) -> Instant | None:
        return Instant(cls._int(value)) if value is not None else None

    @staticmethod
    def _pointer(value: object) -> ArtifactPointer | None:
        return ArtifactPointer(str(value)) if value is not None else None
