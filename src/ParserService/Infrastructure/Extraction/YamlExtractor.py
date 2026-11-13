from typing import cast

import yaml

from ParserService.Domain.Documents.ExtractionRequest import ExtractionRequest
from ParserService.Domain.Documents.ParsedDocument import ParsedDocument
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Infrastructure.Extraction.StructuredDataBuilder import StructuredDataBuilder
from ParserService.Infrastructure.Extraction.TextFileReader import TextFileReader


class YamlExtractor:
    """Extracts YAML using PyYAML's safe loader."""

    def __init__(self, reader: TextFileReader, builder: StructuredDataBuilder) -> None:
        self._reader = reader
        self._builder = builder

    def extract(self, request: ExtractionRequest) -> Result[ParsedDocument, FailureReason]:
        """Load YAML without constructing arbitrary Python objects."""
        source = self._reader.read(request)
        try:
            values = cast("object", yaml.safe_load(source))
        except RecursionError:
            return Result.err(FailureReason.LIMIT_EXCEEDED)
        except (yaml.YAMLError, UnicodeError):
            return Result.err(FailureReason.CORRUPTED_FILE)
        return self._builder.result(request, source, values)
