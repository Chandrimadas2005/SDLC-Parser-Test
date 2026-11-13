from dataclasses import replace
from typing import Final

from ParserService.Application.Dto.SummaryGenerationResult import SummaryGenerationResult
from ParserService.Domain.Documents.ParsedDocument import ParsedDocument
from ParserService.Domain.Documents.ParseWarning import ParseWarning
from ParserService.Domain.Documents.Summary import Summary
from ParserService.Domain.Documents.WarningCode import WarningCode
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Domain.Ports.SummaryGenerator import SummaryGenerator


class GenerateOptionalSummary:
    """Runs the optional summary step, which can never fail the parse (brief, section 2.2).

    Summaries are off by default: without a generator the document comes back as it
    is. When the generator reports a failure, or raises one of the errors a summary
    adapter is expected to raise (I/O, runtime or value errors), the document comes
    back with one ``summary_unavailable`` warning and no summary. Its status, elements
    and existing warnings never change.
    """

    ADAPTER_ERRORS: Final = (OSError, RuntimeError, ValueError)

    def __init__(self, generator: SummaryGenerator | None = None) -> None:
        self._generator = generator

    @property
    def enabled(self) -> bool:
        """Whether a summary generator is configured."""
        return self._generator is not None

    def generate(self, document: ParsedDocument) -> SummaryGenerationResult:
        """Summarise a parse result when summaries are switched on.

        Args:
            document: The parse result.

        Returns:
            The document, flagged when the summary failed, and the summary if one was made.
        """
        if self._generator is None:
            return SummaryGenerationResult(document, None)
        produced = self._produce(self._generator, document)
        if produced.is_err:
            return SummaryGenerationResult(self._flagged(document), None)
        return SummaryGenerationResult(document, produced.unwrap())

    def _produce(
        self, generator: SummaryGenerator, document: ParsedDocument
    ) -> Result[Summary, FailureReason]:
        try:
            return generator.generate(document)
        except self.ADAPTER_ERRORS:
            return Result.err(FailureReason.EXTRACTOR_CRASH)

    @staticmethod
    def _flagged(document: ParsedDocument) -> ParsedDocument:
        warning = ParseWarning(WarningCode.SUMMARY_UNAVAILABLE)
        return replace(document, warnings=(*document.warnings, warning))
