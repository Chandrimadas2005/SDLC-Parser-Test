import json

from ParserService.Application.Dto.BatchFileOutcome import BatchFileOutcome
from ParserService.Application.Dto.BatchFileView import BatchFileView
from ParserService.Application.Dto.ParseBatchSubmitted import ParseBatchSubmitted
from ParserService.Application.Dto.ParseBatchView import ParseBatchView
from ParserService.Infrastructure.Http.BatchResponseField import BatchResponseField as Field


class BatchResponse:
    """Builds the JSON bodies of the multi-file upload endpoints."""

    def submitted(self, batch: ParseBatchSubmitted) -> dict[str, object]:
        """Body of ``202`` after a multi-file upload: the batch and each file's job."""
        files = [self._outcome(outcome) for outcome in batch.files]
        return {Field.BATCH_ID: batch.batch_id.value, Field.FILES: files}

    def status(self, view: ParseBatchView) -> dict[str, object]:
        """Body of the batch status: overall status and each file's job status."""
        files = [self._file(file, with_result=False) for file in view.files]
        return {Field.BATCH_ID: view.batch_id.value, Field.STATUS: view.status, Field.FILES: files}

    def combined(self, view: ParseBatchView) -> dict[str, object]:
        """Body of the combined result: every file's parsed document or failure reason."""
        files = [self._file(file, with_result=True) for file in view.files]
        return {Field.BATCH_ID: view.batch_id.value, Field.STATUS: view.status, Field.FILES: files}

    @staticmethod
    def _outcome(outcome: BatchFileOutcome) -> dict[str, object]:
        body: dict[str, object] = {Field.FILE_NAME: outcome.file_name.value}
        if outcome.submitted is None:
            return body | {Field.ERROR: outcome.error}
        submitted = outcome.submitted
        return body | {
            Field.JOB_ID: submitted.job_id.value,
            Field.STATUS: submitted.status,
            Field.ALREADY_EXISTED: submitted.already_existed,
        }

    @staticmethod
    def _file(file: BatchFileView, *, with_result: bool) -> dict[str, object]:
        status = file.status
        body: dict[str, object] = {
            Field.FILE_NAME: file.file_name.value,
            Field.JOB_ID: status.job_id.value,
            Field.STATUS: status.status,
        }
        if status.failure_reason is not None:
            body[Field.FAILURE_REASON] = status.failure_reason
        if with_result and file.result is not None:
            body[Field.RESULT] = json.loads(file.result)
        return body
