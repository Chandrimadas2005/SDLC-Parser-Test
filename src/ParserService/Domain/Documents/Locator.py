from dataclasses import dataclass
from typing import Self


@dataclass(frozen=True, slots=True)
class Locator:
    """Where a piece of data came from in the source file (brief, section 2.2).

    A locator names a page, a sheet (optionally with a cell range such as
    ``A1:F412``), a slide, or a paragraph. Character offsets narrow it down inside
    the decoded text: zero-based, start inclusive, end exclusive. Pages, slides and
    paragraphs are counted from one. Build one with the ``for_*`` class methods.
    """

    page: int | None = None
    sheet: str | None = None
    cell_range: str | None = None
    slide: int | None = None
    paragraph: int | None = None
    char_start: int | None = None
    char_end: int | None = None

    def __post_init__(self) -> None:
        self._require_anchor()
        self._require_positive_numbers()
        self._require_sheet_for_range()
        self._require_valid_offsets()

    @classmethod
    def for_page(cls, page: int) -> Self:
        """Point at a whole page.

        Args:
            page: One-based page number.

        Returns:
            A page locator.
        """
        return cls(page=page)

    @classmethod
    def for_cells(cls, sheet: str, cell_range: str | None) -> Self:
        """Point at a sheet, or at a cell range inside it.

        Args:
            sheet: Sheet name as it appears in the workbook.
            cell_range: Range such as ``A1:F412``, or ``None`` for the whole sheet.

        Returns:
            A sheet locator.
        """
        return cls(sheet=sheet, cell_range=cell_range)

    @classmethod
    def for_slide(cls, slide: int) -> Self:
        """Point at a whole slide.

        Args:
            slide: One-based slide number.

        Returns:
            A slide locator.
        """
        return cls(slide=slide)

    @classmethod
    def for_text(cls, paragraph: int, char_start: int, char_end: int) -> Self:
        """Point at a paragraph and its character span in the decoded text.

        Args:
            paragraph: One-based paragraph number.
            char_start: Zero-based offset of the first character.
            char_end: Offset just after the last character.

        Returns:
            A text locator.
        """
        return cls(paragraph=paragraph, char_start=char_start, char_end=char_end)

    def _require_anchor(self) -> None:
        if all(anchor is None for anchor in (self.page, self.sheet, self.slide, self.paragraph)):
            message = "a locator needs a page, sheet, slide or paragraph"
            raise ValueError(message)

    def _require_positive_numbers(self) -> None:
        for number in (self.page, self.slide, self.paragraph):
            if number is not None and number < 1:
                message = "pages, slides and paragraphs are counted from 1"
                raise ValueError(message)

    def _require_sheet_for_range(self) -> None:
        if self.sheet is not None and not self.sheet.strip():
            message = "sheet name must not be blank"
            raise ValueError(message)
        if self.cell_range is not None and self.sheet is None:
            message = "a cell range needs a sheet"
            raise ValueError(message)

    def _require_valid_offsets(self) -> None:
        if self.char_start is None and self.char_end is None:
            return
        if self.char_start is None or self.char_end is None:
            message = "character offsets come as a start and end pair"
            raise ValueError(message)
        if not 0 <= self.char_start <= self.char_end:
            message = "character offsets must satisfy 0 <= start <= end"
            raise ValueError(message)
