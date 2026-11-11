"""Compares pypdf, pdfplumber and pypdfium2 on synthetic PDFs (Phase 0, first week)."""

from tools.PdfComparison.ComparisonReport import ComparisonReport
from tools.PdfComparison.ComparisonResult import ComparisonResult
from tools.PdfComparison.PdfComparisonCli import PdfComparisonCli
from tools.PdfComparison.PdfComparisonRunner import PdfComparisonRunner
from tools.PdfComparison.PdfLibrary import PdfLibrary
from tools.PdfComparison.PdfTextExtraction import PdfTextExtraction
from tools.PdfComparison.SyntheticPdf import SyntheticPdf
from tools.PdfComparison.SyntheticPdfFactory import SyntheticPdfFactory

__all__ = [
    "ComparisonReport",
    "ComparisonResult",
    "PdfComparisonCli",
    "PdfComparisonRunner",
    "PdfLibrary",
    "PdfTextExtraction",
    "SyntheticPdf",
    "SyntheticPdfFactory",
]
