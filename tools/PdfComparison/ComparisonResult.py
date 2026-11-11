from dataclasses import dataclass

from tools.PdfComparison.PdfLibrary import PdfLibrary


@dataclass(frozen=True, slots=True)
class ComparisonResult:
    """How one library did on one sample: speed and how much text it recovered.

    ``word_recall`` is the share of expected words found, page by page.
    ``order_score`` is how closely the extracted word order matches the expected
    reading order (1.0 is identical).
    """

    library: PdfLibrary
    page_count: int
    milliseconds: float
    pages_found: int
    word_recall: float
    order_score: float
