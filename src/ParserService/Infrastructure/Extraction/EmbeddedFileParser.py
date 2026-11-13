import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Final

from ParserService.Domain.Documents.ParsedDocument import ParsedDocument
from ParserService.Domain.Documents.SourceFile import SourceFile
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Domain.Jobs.FileName import FileName
from ParserService.Infrastructure.Extraction.EmbeddedFile import EmbeddedFile

if TYPE_CHECKING:
    # ParsePipeline imports the registry, which builds this parser: type-only import.
    from ParserService.Infrastructure.Extraction.ParsePipeline import ParsePipeline


class EmbeddedFileParser:
    """Parses a file found inside another one with the normal detection and extractors.

    The file is written to a private temporary folder under a fixed name (only its
    extension is kept, as a detection hint), so names such as ``../../etc/passwd``
    inside an archive can never write outside that folder. ``depth`` says how deep
    the file sits, so nested archives can be capped.
    """

    FALLBACK_NAME: Final = "embedded"
    MAX_SUFFIX: Final = 10

    def __init__(self, depth: int, pipeline: Callable[[], "ParsePipeline"]) -> None:
        self.depth = depth
        self._pipeline = pipeline

    def parse(self, file: EmbeddedFile) -> Result[ParsedDocument, FailureReason]:
        """Detect and extract one embedded file.

        Args:
            file: The file's name and bytes.

        Returns:
            Its parsed document, or why it could not be parsed.
        """
        suffix = Path(file.name).suffix[: self.MAX_SUFFIX]
        name = Path(file.name.replace("\\", "/")).name or self.FALLBACK_NAME
        with tempfile.TemporaryDirectory(prefix="embedded-") as folder:
            path = Path(folder) / f"{self.FALLBACK_NAME}{suffix}"
            path.write_bytes(file.content)
            return self._pipeline().parse(SourceFile(str(path), self._file_name(name)))

    def _file_name(self, name: str) -> FileName:
        try:
            return FileName(name)
        except ValueError:
            return FileName(self.FALLBACK_NAME)
