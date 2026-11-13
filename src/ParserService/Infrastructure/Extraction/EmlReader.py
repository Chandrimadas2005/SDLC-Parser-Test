from __future__ import annotations

from email import policy
from email.errors import MessageError
from email.message import EmailMessage, Message
from email.parser import BytesParser
from typing import TYPE_CHECKING, Final

from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Infrastructure.Extraction.EmbeddedFile import EmbeddedFile
from ParserService.Infrastructure.Extraction.MailContent import MailContent
from ParserService.Infrastructure.Extraction.MailHeader import MailHeader

if TYPE_CHECKING:
    from pathlib import Path


class EmlReader:
    """Reads an RFC 822 e-mail (EML) with the standard library's parser."""

    HEADERS: Final = {
        MailHeader.SUBJECT: "subject",
        MailHeader.FROM: "from",
        MailHeader.TO: "to",
        MailHeader.DATE: "date",
    }
    FALLBACK_NAME: Final = "attachment"

    def read(self, path: Path) -> Result[MailContent, FailureReason]:
        """Read an EML file.

        Args:
            path: The file.

        Returns:
            Its headers, bodies and attachments, or ``corrupted_file``.
        """
        try:
            with path.open("rb") as handle:
                message = BytesParser(policy=policy.default).parse(handle)
        except (MessageError, OSError, UnicodeError):
            return Result.err(FailureReason.CORRUPTED_FILE)
        if not isinstance(message, EmailMessage) or not message.keys():
            return Result.err(FailureReason.CORRUPTED_FILE)
        return Result.ok(self._content(message))

    def _content(self, message: EmailMessage[str, str]) -> MailContent:
        headers = {key: str(message.get(name, "")) for key, name in self.HEADERS.items()}
        attachments = tuple(self._attachment(part) for part in message.iter_attachments())
        return MailContent(
            headers, self._body(message, "plain"), self._body(message, "html"), attachments
        )

    @staticmethod
    def _body(message: EmailMessage[str, str], subtype: str) -> str | None:
        part = message.get_body(preferencelist=(subtype,))
        if not isinstance(part, EmailMessage):
            return None
        content = part.get_content()
        return content if isinstance(content, str) else None

    def _attachment(self, part: Message[str, str]) -> EmbeddedFile:
        payload = part.get_payload(decode=True)
        content = payload if isinstance(payload, bytes) else b""
        return EmbeddedFile(part.get_filename() or self.FALLBACK_NAME, content)
