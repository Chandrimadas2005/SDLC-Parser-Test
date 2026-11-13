import io
from pathlib import Path

from ParserService.Domain.Jobs import FailureReason
from ParserService.Infrastructure.Extraction import MailHeader, MsgReader


class _FakeOle:
    """Stands in for olefile.OleFileIO with a few MAPI property streams."""

    def __init__(self, streams: dict[str, bytes]) -> None:
        self._streams = streams

    def listdir(self) -> list[list[str]]:
        return [name.split("/") for name in self._streams]

    def exists(self, path: str) -> bool:
        return path in self._streams

    def openstream(self, path: str) -> io.BytesIO:
        return io.BytesIO(self._streams[path])


class TestMsgReader:
    """Outlook messages: headers, body and attachments come from their MAPI streams."""

    @staticmethod
    def _text(value: str) -> bytes:
        return value.encode("utf-16-le")

    def test_headers_body_and_attachments_are_read(self) -> None:
        attachment = "__attach_version1.0_#00000000"
        ole = _FakeOle(
            {
                "__substg1.0_0037001F": self._text("Synthetic subject"),
                "__substg1.0_0C1A001F": self._text("Asha"),
                "__substg1.0_1000001F": self._text("Synthetic body."),
                f"{attachment}/__substg1.0_3707001F": self._text("tasks.csv"),
                f"{attachment}/__substg1.0_37010102": b"Task ID,Owner\nT-1,Asha\n",
            }
        )

        mail = MsgReader().content(ole)

        assert mail.headers[MailHeader.SUBJECT] == "Synthetic subject"
        assert mail.headers[MailHeader.FROM] == "Asha"
        assert mail.text == "Synthetic body."
        assert [(a.name, a.content[:7]) for a in mail.attachments] == [("tasks.csv", b"Task ID")]

    def test_a_file_that_is_not_ole_is_corrupted(self, tmp_path: Path) -> None:
        path = tmp_path / "x.msg"
        path.write_bytes(b"plain bytes")

        assert MsgReader().read(path).unwrap_err() is FailureReason.CORRUPTED_FILE
