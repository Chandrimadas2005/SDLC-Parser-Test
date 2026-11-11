import dataclasses

import pytest

from ParserService.Domain.Documents import (
    DetectedType,
    DocumentFacts,
    DocumentStatus,
    ElementKind,
    MetricName,
    Metrics,
    ParsedDocument,
)
from ParserService.Domain.Jobs import FailureReason, FileHash, FileName
from tests.Samples import DocumentSamples


class TestParsedDocument:
    """A ParsedDocument is always internally consistent."""

    SAMPLES = DocumentSamples()

    def test_samples_are_valid_and_count_their_warnings(self) -> None:
        assert self.SAMPLES.text_document().warning_count == 0
        assert self.SAMPLES.spreadsheet().warning_count == 1
        assert self.SAMPLES.failed().failure_reason is FailureReason.PASSWORD_PROTECTED
        assert ParsedDocument.SCHEMA_VERSION == "1.1"

    def test_failure_reason_belongs_to_failed_results_only(self) -> None:
        failed = self.SAMPLES.failed()

        with pytest.raises(ValueError, match="needs a failure reason"):
            dataclasses.replace(failed, failure_reason=None)
        with pytest.raises(ValueError, match="only failed"):
            dataclasses.replace(failed, status=DocumentStatus.SUCCEEDED)

    def test_partial_result_must_say_what_is_missing(self) -> None:
        with pytest.raises(ValueError, match="what is missing"):
            dataclasses.replace(self.SAMPLES.spreadsheet(), warnings=())

    def test_element_ids_are_unique(self) -> None:
        document = self.SAMPLES.text_document()
        duplicated = (document.elements[0], document.elements[0])

        with pytest.raises(ValueError, match="unique"):
            dataclasses.replace(document, elements=duplicated)

    def test_metrics_count_elements_by_kind_in_a_fixed_order(self) -> None:
        metrics = self.SAMPLES.text_document().metrics

        assert list(metrics.elements_by_kind.items()) == [
            (ElementKind.HEADING, 1),
            (ElementKind.PARAGRAPH, 1),
        ]
        with pytest.raises(ValueError, match="negative"):
            Metrics(counts={MetricName.ROWS: -1}, elements_by_kind={})

    def test_facts_reject_negative_sizes_and_counts(self) -> None:
        name, digest = FileName("a.pdf"), FileHash.of(b"x")

        with pytest.raises(ValueError, match="size"):
            DocumentFacts(name, DetectedType.PDF, -1, digest)
        with pytest.raises(ValueError, match="counts"):
            DocumentFacts(name, DetectedType.PDF, 1, digest, page_count=-1)
