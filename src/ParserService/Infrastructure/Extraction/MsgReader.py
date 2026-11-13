from pathlib import Path
from typing import Final

import olefile

from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Infrastructure.Extraction.EmbeddedFile import EmbeddedFile
from ParserService.Infrastructure.Extraction.MailContent import MailContent
from ParserService.Infrastructure.Extraction.MailHeader import MailHeader


class MsgReader:
    """Reads an Outlook message (MSG), an OLE compound file, with olefile (BSD).

    Each MAPI property is a stream named ``__substg1.0_<id><type>``; ``001F`` is
    UTF-16 text and ``0102`` is binary. Attachments are storages named
    ``__attach_version1.0_#NNNNNNNN``. Only these streams are read; nothing runs.
    """

    TEXT: Final = "001F"
    BINARY: Final = "0102"
    HEADERS: Final = {
        MailHeader.SUBJECT: "0037",
        MailHeader.FROM: "0C1A",
        MailHeader.TO: "0E04",
        MailHeader.DATE: "0039",
    }
    BODY: Final = "1000"
    HTML: Final = "1013"
    ATTACHMENT: Final = "__attach_version1.0_#"
    ATTACH_DATA: Final = "3701"
    ATTACH_NAMES: Final = ("3707", "3704")
    FALLBACK_NAME: Final = "attachment"

    def read(self, path: Path) -> Result[MailContent, FailureReason]:
        """Read an MSG file.

        Args:
            path: The file.

        Returns:
            Its headers, bodies and attachments, or ``corrupted_file``.
        """
        if not olefile.isOleFile(str(path)):
            return Result.err(FailureReason.CORRUPTED_FILE)
        try:
            with olefile.OleFileIO(str(path)) as ole:
                return Result.ok(self.content(ole))
        except (OSError, ValueError, IndexError):
            return Result.err(FailureReason.CORRUPTED_FILE)

    def content(self, ole: olefile.OleFileIO) -> MailContent:
        """Read the headers, bodies and attachments of an open MSG file.

        Args:
            ole: The open compound file.

        Returns:
            What the message holds.
        """
        headers = {key: self._text(ole, "", prop) or "" for key, prop in self.HEADERS.items()}
        html = self._binary(ole, "", self.HTML)
        attachments = tuple(self._attachment(ole, folder) for folder in self._folders(ole))
        text = self._text(ole, "", self.BODY)
        return MailContent(
            headers, text, html.decode("utf-8", "replace") if html else None, attachments
        )

    def _folders(self, ole: olefile.OleFileIO) -> list[str]:
        names = {entry[0] for entry in ole.listdir() if entry[0].startswith(self.ATTACHMENT)}
        return sorted(names)

    def _attachment(self, ole: olefile.OleFileIO, folder: str) -> EmbeddedFile:
        names = (self._text(ole, folder, prop) for prop in self.ATTACH_NAMES)
        name = next((found for found in names if found), self.FALLBACK_NAME)
        return EmbeddedFile(name, self._binary(ole, folder, self.ATTACH_DATA) or b"")

    def _text(self, ole: olefile.OleFileIO, folder: str, prop: str) -> str | None:
        raw = self._stream(ole, folder, f"{prop}{self.TEXT}")
        return None if raw is None else raw.decode("utf-16-le", "replace").rstrip("\x00")

    def _binary(self, ole: olefile.OleFileIO, folder: str, prop: str) -> bytes | None:
        return self._stream(ole, folder, f"{prop}{self.BINARY}")

    @staticmethod
    def _stream(ole: olefile.OleFileIO, folder: str, name: str) -> bytes | None:
        path = f"{folder}/__substg1.0_{name}" if folder else f"__substg1.0_{name}"
        if not ole.exists(path):
            return None
        data = ole.openstream(path).read()
        return data if isinstance(data, bytes) else None
