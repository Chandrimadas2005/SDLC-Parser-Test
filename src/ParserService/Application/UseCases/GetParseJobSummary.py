from ParserService.Application.Errors.ApplicationErrorCode import ApplicationErrorCode
from ParserService.Application.UseCases.GetParseJobResult import GetParseJobResult
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.JobId import JobId
from ParserService.Domain.Ports.ResultSummaryRenderer import ResultSummaryRenderer


class GetParseJobSummary:
    """Builds a short summary of a completed job's result, on request.

    The summary is kept outside the stored ``ParsedDocument`` (brief, section 2.2):
    it is rendered here from the same JSON result ``/result`` serves, never stored
    on its own, so it never changes the schema or the parse outcome.
    """

    def __init__(self, results: GetParseJobResult, renderer: ResultSummaryRenderer) -> None:
        self._results = results
        self._renderer = renderer

    def execute(self, job_id: JobId) -> Result[str, ApplicationErrorCode]:
        """Return a plain-text summary of the job's result.

        Args:
            job_id: The job whose result is summarised.

        Returns:
            The summary, or the same error ``GetParseJobResult`` would give (the job
            is not found, failed, not finished yet, or its result is missing).
        """
        content = self._results.execute(job_id)
        if content.is_err:
            return Result.err(content.unwrap_err())
        return Result.ok(self._renderer.render(content.unwrap()))
