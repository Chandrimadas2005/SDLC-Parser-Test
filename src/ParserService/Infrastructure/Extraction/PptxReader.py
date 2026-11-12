import posixpath
import zipfile
from pathlib import Path

from defusedxml import ElementTree

from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Infrastructure.Extraction.PptxPart import PptxPart
from ParserService.Infrastructure.Extraction.PptxSlide import PptxSlide
from ParserService.Infrastructure.Extraction.PptxSlideReader import PptxSlideReader
from ParserService.Infrastructure.Extraction.SlideTag import SlideTag


class PptxReader:
    """Reads a PPTX package directly as XML, with defusedxml, slide by slide.

    Slides are read in presentation order. A slide whose XML is broken is reported
    as unreadable and the others are still read. Macros, embedded objects and media
    are never opened.
    """

    def __init__(self, slides: PptxSlideReader) -> None:
        self._slides = slides

    def read(self, path: Path) -> Result[tuple[PptxSlide, ...], FailureReason]:
        """Read every slide.

        Args:
            path: The PPTX file.

        Returns:
            The slides, or ``corrupted_file`` when the package itself is broken.
        """
        try:
            with zipfile.ZipFile(path) as package:
                parts = self._slide_parts(package)
                return Result.ok(tuple(self._slide(package, part) for part in parts))
        except (zipfile.BadZipFile, KeyError, ElementTree.ParseError, OSError):
            return Result.err(FailureReason.CORRUPTED_FILE)

    @staticmethod
    def _slide_parts(package: zipfile.ZipFile) -> list[tuple[int, str]]:
        presentation = ElementTree.fromstring(package.read(PptxPart.PRESENTATION))
        relations = ElementTree.fromstring(package.read(PptxPart.RELATIONSHIPS))
        targets = {
            rel.get(PptxPart.ID, ""): rel.get(PptxPart.TARGET, "")
            for rel in relations.iter(SlideTag.RELATIONSHIP)
        }
        ids = [
            node.get(SlideTag.RELATIONSHIP_ID, "") for node in presentation.iter(SlideTag.SLIDE_ID)
        ]
        paths = [posixpath.normpath(posixpath.join(PptxPart.FOLDER, targets[i])) for i in ids]
        return list(enumerate(paths, 1))

    def _slide(self, package: zipfile.ZipFile, part: tuple[int, str]) -> PptxSlide:
        number, path = part
        try:
            root = ElementTree.fromstring(package.read(path))
        except (KeyError, ElementTree.ParseError):
            return PptxSlide(number, None, (), readable=False)
        return self._slides.read(root, number)
