import hashlib
from pathlib import Path
from typing import Final, Self

from ParserService.Domain.Documents.Detection import Detection
from ParserService.Domain.Documents.DocumentFacts import DocumentFacts
from ParserService.Domain.Documents.ExtractionRequest import ExtractionRequest
from ParserService.Domain.Documents.ParsedDocument import ParsedDocument
from ParserService.Domain.Documents.PropertyName import PropertyName
from ParserService.Domain.Documents.SourceFile import SourceFile
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Domain.Jobs.FileHash import FileHash
from ParserService.Domain.Ports.TypeDetector import TypeDetector
from ParserService.Infrastructure.Config.Limits import Limits
from ParserService.Infrastructure.Detection.MagicTypeDetector import MagicTypeDetector
from ParserService.Infrastructure.Detection.TextEncodingDetector import TextEncodingDetector
from ParserService.Infrastructure.Detection.ZipContentInspector import ZipContentInspector
from ParserService.Infrastructure.Extraction.ExtractorRegistry import ExtractorRegistry


class ParsePipeline:
    """Parses one file end to end: detect the type, pick the extractor, extract.

    The file facts (size and SHA-256) are computed here, reading the file in chunks
    so a large file never sits in memory whole.
    """

    CHUNK_BYTES: Final = 1024 * 1024

    def __init__(self, detector: TypeDetector, registry: ExtractorRegistry) -> None:
        self._detector = detector
        self._registry = registry

    @classmethod
    def default(cls, limits: Limits | None = None) -> Self:
        """Build the pipeline with the content-based detector and every extractor.

        Used by the command line tool, so it parses exactly as the worker does.

        Args:
            limits: The page and archive limits; the defaults when not given.

        Returns:
            The pipeline.
        """
        chosen = limits or Limits()
        detector = MagicTypeDetector(TextEncodingDetector(), ZipContentInspector())
        return cls(detector, ExtractorRegistry.default(chosen.max_pages, chosen))

    def parse(self, source: SourceFile) -> Result[ParsedDocument, FailureReason]:
        """Parse a file.

        Args:
            source: The file to parse.

        Returns:
            The parsed document, or why the file could not be parsed.
        """
        detected = self._detector.detect(source)
        if detected.is_err:
            return Result.err(detected.unwrap_err())
        detection = detected.unwrap()
        extractor = self._registry.for_type(detection.detected_type)
        if extractor.is_err:
            return Result.err(extractor.unwrap_err())
        request = ExtractionRequest(source, self._facts(source, detection), detection)
        return extractor.unwrap().extract(request)

    def _facts(self, source: SourceFile, detection: Detection) -> DocumentFacts:
        path = Path(source.location)
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(self.CHUNK_BYTES), b""):
                digest.update(chunk)
        size = path.stat().st_size
        sha256 = FileHash(digest.hexdigest())
        facts = DocumentFacts(source.file_name, detection.detected_type, size, sha256)
        return facts.with_properties({PropertyName.ENCODING: detection.encoding or ""})
