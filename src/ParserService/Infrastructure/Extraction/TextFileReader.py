from pathlib import Path
from typing import Final

from ParserService.Domain.Documents.ExtractionRequest import ExtractionRequest


class TextFileReader:
    """Decodes a text file with the encoding detection found.

    Line endings are kept as they are, so character offsets match the file. Bytes
    that do not decode are replaced, never dropped silently: detection already
    flags a guessed encoding with a warning.
    """

    FALLBACK_ENCODING: Final = "utf_8"

    def read(self, request: ExtractionRequest) -> str:
        """Read the whole decoded text of the file.

        Args:
            request: The file and its detection.

        Returns:
            The decoded text.
        """
        encoding = request.detection.encoding or self.FALLBACK_ENCODING
        path = Path(request.source.location)
        with path.open(encoding=encoding, errors="replace", newline="") as handle:
            return handle.read()
