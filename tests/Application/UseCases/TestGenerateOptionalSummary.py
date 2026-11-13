from dataclasses import replace

import pytest

from ParserService.Application.UseCases import GenerateOptionalSummary
from ParserService.Domain.Documents import DocumentStatus, ParseWarning, Summary, WarningCode
from ParserService.Domain.Errors import Result
from ParserService.Domain.Jobs import FailureReason
from tests.Fakes import FakeSummaryGenerator
from tests.Samples import DocumentSamples

SUMMARY_UNAVAILABLE = ParseWarning(WarningCode.SUMMARY_UNAVAILABLE)


class TestGenerateOptionalSummary:
    """The optional summary is off by default and can never fail or change the parse."""

    def test_is_off_by_default(self) -> None:
        document = DocumentSamples().text_document()
        use_case = GenerateOptionalSummary()

        result = use_case.generate(document)

        assert not use_case.enabled
        assert result.document is document
        assert result.summary is None

    def test_a_generated_summary_keeps_the_document_unchanged(self) -> None:
        document = DocumentSamples().text_document()
        generator = FakeSummaryGenerator(Result.ok(Summary("Synthetic summary")))

        result = GenerateOptionalSummary(generator).generate(document)

        assert result.document is document
        assert result.summary == Summary("Synthetic summary")
        assert generator.documents == [document]

    def test_a_reported_failure_only_adds_a_warning(self) -> None:
        document = DocumentSamples().spreadsheet()
        generator = FakeSummaryGenerator(Result.err(FailureReason.TIMEOUT))

        result = GenerateOptionalSummary(generator).generate(document)

        assert result.summary is None
        assert result.document.status is DocumentStatus.PARTIAL
        assert result.document == replace(
            document, warnings=(*document.warnings, SUMMARY_UNAVAILABLE)
        )

    @pytest.mark.parametrize("error", [RuntimeError("down"), ValueError("bad"), OSError("io")])
    def test_an_adapter_error_only_adds_a_warning(self, error: Exception) -> None:
        document = DocumentSamples().text_document()

        result = GenerateOptionalSummary(FakeSummaryGenerator(error=error)).generate(document)

        assert result.summary is None
        assert result.document.status is DocumentStatus.SUCCEEDED
        assert result.document.warnings == (SUMMARY_UNAVAILABLE,)
        assert result.document.elements == document.elements

    def test_an_unexpected_error_is_not_hidden(self) -> None:
        generator = FakeSummaryGenerator(error=KeyError("bug"))

        with pytest.raises(KeyError, match="bug"):
            GenerateOptionalSummary(generator).generate(DocumentSamples().text_document())

    def test_blank_summaries_are_rejected(self) -> None:
        with pytest.raises(ValueError, match="blank"):
            Summary("   ")
