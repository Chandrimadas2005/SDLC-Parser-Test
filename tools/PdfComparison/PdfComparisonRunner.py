import time
from collections import Counter
from difflib import SequenceMatcher
from statistics import fmean
from typing import Final

from tools.PdfComparison.ComparisonResult import ComparisonResult
from tools.PdfComparison.PdfLibrary import PdfLibrary
from tools.PdfComparison.PdfTextExtraction import PdfTextExtraction
from tools.PdfComparison.SyntheticPdf import SyntheticPdf


class PdfComparisonRunner:
    """Runs every library on a sample and scores speed, recall and reading order."""

    REPEATS: Final = 3

    def __init__(self, extraction: PdfTextExtraction) -> None:
        self._extraction = extraction

    def compare(self, sample: SyntheticPdf) -> list[ComparisonResult]:
        """Compare all libraries on one sample.

        Args:
            sample: The generated PDF and its expected words.

        Returns:
            One result per library, in ``PdfLibrary`` order.
        """
        return [self._measure(library, sample) for library in PdfLibrary]

    def _measure(self, library: PdfLibrary, sample: SyntheticPdf) -> ComparisonResult:
        timings: list[float] = []
        pages: list[str] = []
        for _ in range(self.REPEATS):
            started = time.perf_counter()
            pages = self._extraction.pages(library, sample.path)
            timings.append((time.perf_counter() - started) * 1000)
        found = [tuple(text.split()) for text in pages]
        pairs = list(zip(sample.expected_pages, found, strict=False))
        recall = fmean(self._recall(expected, got) for expected, got in pairs)
        order = fmean(self._order(expected, got) for expected, got in pairs)
        return ComparisonResult(library, sample.page_count, min(timings), len(pages), recall, order)

    @staticmethod
    def _recall(expected: tuple[str, ...], found: tuple[str, ...]) -> float:
        matched = Counter(expected) & Counter(found)
        return sum(matched.values()) / len(expected)

    @staticmethod
    def _order(expected: tuple[str, ...], found: tuple[str, ...]) -> float:
        return SequenceMatcher(None, expected, found, autojunk=False).ratio()
