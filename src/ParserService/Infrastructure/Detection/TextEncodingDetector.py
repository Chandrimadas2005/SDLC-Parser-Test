from typing import Final

from charset_normalizer import from_bytes


class TextEncodingDetector:
    """Finds the character encoding of text bytes with charset-normalizer.

    Empty content counts as UTF-8. Content that no text encoding explains is binary.
    """

    UTF8: Final = "utf_8"
    CERTAIN: Final = frozenset({"ascii", "utf_8"})

    def encoding(self, sample: bytes) -> str | None:
        """Detect the encoding of a sample of the file.

        Args:
            sample: The first bytes of the file.

        Returns:
            The Python codec name, or ``None`` when the bytes are not text.
        """
        if not sample:
            return self.UTF8
        best = from_bytes(sample).best()
        return None if best is None else best.encoding

    def is_guess(self, encoding: str) -> bool:
        """Tell whether an encoding was guessed rather than certain.

        Args:
            encoding: A codec name returned by ``encoding``.

        Returns:
            ``True`` for anything other than ASCII or UTF-8.
        """
        return encoding not in self.CERTAIN
