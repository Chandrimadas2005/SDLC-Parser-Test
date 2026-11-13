from ParserService.Application.Dto.BatchFileView import BatchFileView
from ParserService.Application.Dto.ParseBatchView import ParseBatchView
from ParserService.Application.Errors.ApplicationErrorCode import ApplicationErrorCode
from ParserService.Application.UseCases.GetParseJobResult import GetParseJobResult
from ParserService.Application.UseCases.GetParseJobStatus import GetParseJobStatus
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.BatchEntry import BatchEntry
from ParserService.Domain.Jobs.BatchId import BatchId
from ParserService.Domain.Ports.BatchStore import BatchStore


class GetParseBatch:
    """Reads a batch: every file's job status and, for the combined result, its result."""

    def __init__(
        self, batches: BatchStore, statuses: GetParseJobStatus, results: GetParseJobResult
    ) -> None:
        self._batches = batches
        self._statuses = statuses
        self._results = results

    def status(self, batch_id: BatchId) -> Result[ParseBatchView, ApplicationErrorCode]:
        """Every file's job status.

        Args:
            batch_id: The batch to read.

        Returns:
            The batch view, or ``BATCH_NOT_FOUND``.
        """
        return self._view(batch_id, with_results=False)

    def combined(self, batch_id: BatchId) -> Result[ParseBatchView, ApplicationErrorCode]:
        """Every file's status and result, once all of them have finished.

        Args:
            batch_id: The batch to read.

        Returns:
            The batch view with results, ``BATCH_NOT_FOUND``, or
            ``RESULT_NOT_READY`` while any file is still queued or running.
        """
        view = self._view(batch_id, with_results=False)
        if view.is_err or not view.unwrap().finished:
            return view if view.is_err else Result.err(ApplicationErrorCode.RESULT_NOT_READY)
        return self._view(batch_id, with_results=True)

    def _view(
        self, batch_id: BatchId, *, with_results: bool
    ) -> Result[ParseBatchView, ApplicationErrorCode]:
        batch = self._batches.load(batch_id)
        if batch is None:
            return Result.err(ApplicationErrorCode.BATCH_NOT_FOUND)
        views = (self._file(entry, with_results=with_results) for entry in batch.entries)
        return Result.ok(ParseBatchView(batch.id, tuple(v for v in views if v is not None)))

    def _file(self, entry: BatchEntry, *, with_results: bool) -> BatchFileView | None:
        # A job deleted after the upload simply drops out of its batch.
        status = self._statuses.execute(entry.job_id)
        if status.is_err:
            return None
        result = self._results.execute(entry.job_id) if with_results else None
        content = result.unwrap() if result is not None and result.is_ok else None
        return BatchFileView(entry.file_name, status.unwrap(), content)
