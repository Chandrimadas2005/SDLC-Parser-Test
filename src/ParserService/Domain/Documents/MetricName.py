from enum import StrEnum


class MetricName(StrEnum):
    """The counts recorded for every file (brief, section 2.2).

    Counts of elements by kind are kept separately, keyed by ``ElementKind``.
    """

    WORDS = "words"
    PAGES = "pages"
    SHEETS = "sheets"
    SLIDES = "slides"
    ROWS = "rows"
    COLUMNS = "columns"
    FORMULAS = "formulas"
    HIDDEN_SHEETS = "hidden_sheets"
