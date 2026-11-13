from collections.abc import Sequence

from ParserService.Application.Dto.BatchFileOutcome import BatchFileOutcome
from ParserService.Application.Dto.ParseBatchSubmitted import ParseBatchSubmitted
from ParserService.Application.Dto.SubmitParseJobCommand import SubmitParseJobCommand
from ParserService.Application.Errors.ApplicationErrorCode import ApplicationErrorCode
from ParserService.Application.UseCases.SubmitParseJob import SubmitParseJob
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.BatchEntry import BatchEntry
from ParserService.Domain.Jobs.BatchId import BatchId
from ParserService.Domain.Jobs.ParseBatch import ParseBatch
from ParserService.Domain.Ports.BatchStore import BatchStore


class SubmitParseBatch:
    """Accepts several files in one upload: one job per file, grouped as a batch.

    Every file goes through the normal submission (size check, duplicate rule,
    queue), so the files are parsed in parallel by the worker slots. A file that is
    refused (for example too large) is reported in the answer; the others still run.
    """

    def __init__(self, submit: SubmitParseJob, batches: BatchStore, max_files: int) -> None:
        self._submit = submit
        self._batches = batches
        self._max_files = max_files

    def execute(
        self, commands: Sequence[SubmitParseJobCommand]
    ) -> Result[ParseBatchSubmitted, ApplicationErrorCode]:
        """Submit every file and remember them as one batch.

        Args:
            commands: The uploaded files, in upload order.

        Returns:
            The batch and each file's outcome, ``BATCH_TOO_LARGE`` above the file
            limit, or the first file's error when no file was accepted.
        """
        if len(commands) > self._max_files:
            return Result.err(ApplicationErrorCode.BATCH_TOO_LARGE)
        outcomes = tuple(self._one(command) for command in commands)
        entries = tuple(
            BatchEntry(outcome.file_name, outcome.submitted.job_id)
            for outcome in outcomes
            if outcome.submitted is not None
        )
        if not entries:
            return Result.err(outcomes[0].error or ApplicationErrorCode.INVALID_REQUEST)
        batch = ParseBatch(BatchId.new(), entries)
        self._batches.save(batch)
        return Result.ok(ParseBatchSubmitted(batch.id, outcomes))

    def _one(self, command: SubmitParseJobCommand) -> BatchFileOutcome:
        result = self._submit.execute(command)
        if result.is_err:
            return BatchFileOutcome(command.file_name, None, result.unwrap_err())
        return BatchFileOutcome(command.file_name, result.unwrap(), None)
