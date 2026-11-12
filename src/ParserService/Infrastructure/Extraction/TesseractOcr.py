import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import ClassVar, Final, Self

from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Infrastructure.Extraction.OcrText import OcrText


class TesseractOcr:
    """Runs the Tesseract OCR engine as its own process and reads its word-level output.

    Tesseract's TSV output gives every word with its block, paragraph and line, and a
    confidence from 0 to 100. Words are joined back into lines and paragraphs, and
    the confidence is the mean over all words, scaled to 0-1.
    """

    EXECUTABLE: ClassVar[str] = "tesseract"
    TIMEOUT_SECONDS: ClassVar[float] = 60
    LANGUAGE: Final = "eng"
    WORD_LEVEL: Final = "5"
    COLUMNS: Final = 12

    def __init__(self, executable: str) -> None:
        self._executable = executable

    @classmethod
    def available(cls) -> Self | None:
        """Find Tesseract on this machine.

        Returns:
            An OCR engine, or ``None`` when Tesseract is not installed.
        """
        executable = shutil.which(cls.EXECUTABLE)
        return None if executable is None else cls(executable)

    def read(self, image: Path) -> Result[OcrText, FailureReason]:
        """Recognise the text in an image.

        Args:
            image: A PNG, JPEG, TIFF or PNM image.

        Returns:
            The text and its confidence, or ``corrupted_file`` when Tesseract fails.
        """
        command = [self._executable, str(image), "stdout", "-l", self.LANGUAGE, "tsv"]
        try:
            completed = subprocess.run(  # noqa: S603 - fixed Tesseract command
                command, capture_output=True, text=True, timeout=self.TIMEOUT_SECONDS, check=False
            )
        except subprocess.TimeoutExpired:
            return Result.err(FailureReason.TIMEOUT)
        if completed.returncode != 0:
            return Result.err(FailureReason.CORRUPTED_FILE)
        return Result.ok(self._text(list(self._words(completed.stdout))))

    def _words(self, tsv: str) -> Iterator[tuple[tuple[str, str, str], str, float]]:
        for line in tsv.splitlines()[1:]:
            cells = line.split("\t")
            if len(cells) == self.COLUMNS and cells[0] == self.WORD_LEVEL and cells[11].strip():
                yield (cells[2], cells[3], cells[4]), cells[11], float(cells[10])

    @staticmethod
    def _text(words: list[tuple[tuple[str, str, str], str, float]]) -> OcrText:
        lines: dict[tuple[str, str, str], list[str]] = {}
        for position, word, _ in words:
            lines.setdefault(position, []).append(word)
        paragraphs: dict[tuple[str, str], list[str]] = {}
        for (block, paragraph, _), line_words in lines.items():
            paragraphs.setdefault((block, paragraph), []).append(" ".join(line_words))
        text = "\n\n".join("\n".join(lines_) for lines_ in paragraphs.values())
        confidence = sum(score for *_, score in words) / len(words) / 100 if words else 0.0
        return OcrText(text, round(min(max(confidence, 0.0), 1.0), 2))
