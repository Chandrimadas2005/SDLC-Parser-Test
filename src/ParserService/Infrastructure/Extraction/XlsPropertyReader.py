import io
import struct
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Final

from xlrd import compdoc  # type: ignore[import-untyped]

from ParserService.Domain.Documents import PropertyName


class XlsPropertyReader:
    """Reads a legacy XLS workbook's own metadata (brief, section 2.2, file properties).

    Title, author, dates and the like live in the OLE ``SummaryInformation`` and
    ``DocumentSummaryInformation`` property-set streams, which xlrd does not parse.
    They are read here with xlrd's own compound-document reader (no extra library) and
    decoded per [MS-OLEPS]. A missing or damaged stream simply adds no properties.
    """

    SUMMARY: Final = "\x05SummaryInformation"
    DOCUMENT_SUMMARY: Final = "\x05DocumentSummaryInformation"
    SUMMARY_FIELDS: Final[Mapping[int, PropertyName]] = {
        2: PropertyName.TITLE,
        3: PropertyName.SUBJECT,
        4: PropertyName.CREATOR,
        5: PropertyName.KEYWORDS,
        6: PropertyName.DESCRIPTION,
        8: PropertyName.LAST_MODIFIED_BY,
        9: PropertyName.REVISION,
        11: PropertyName.LAST_PRINTED,
        12: PropertyName.CREATED,
        13: PropertyName.MODIFIED,
        18: PropertyName.APPLICATION,
    }
    DOCUMENT_FIELDS: Final[Mapping[int, PropertyName]] = {
        2: PropertyName.CATEGORY,
        14: PropertyName.MANAGER,
        15: PropertyName.COMPANY,
    }
    CODEPAGE_ID: Final = 1
    UNICODE_CODEPAGE: Final = 1200
    DEFAULT_CODEPAGE: Final = 1252
    FIRST_SECTION_OFFSET: Final = 44
    VT_LPSTR: Final = 0x1E
    VT_LPWSTR: Final = 0x1F
    VT_FILETIME: Final = 0x40
    FILETIME_EPOCH: Final = datetime(1601, 1, 1, tzinfo=UTC)

    def read(self, path: Path) -> dict[str, str]:
        """Read the workbook's summary and document summary properties.

        Args:
            path: The XLS file.

        Returns:
            Non-empty property values keyed by ``PropertyName``.
        """
        summary, document = self._streams(path)
        return {
            **self._safe_parse(document, self.DOCUMENT_FIELDS),
            **self._safe_parse(summary, self.SUMMARY_FIELDS),
        }

    def _streams(self, path: Path) -> tuple[bytes | None, bytes | None]:
        try:
            document = compdoc.CompDoc(path.read_bytes(), logfile=io.StringIO())
            summary = document.get_named_stream(self.SUMMARY)
            return summary, document.get_named_stream(self.DOCUMENT_SUMMARY)
        except (OSError, compdoc.CompDocError):
            return None, None

    def _safe_parse(
        self, stream: bytes | None, fields: Mapping[int, PropertyName]
    ) -> dict[str, str]:
        if stream is None:
            return {}
        try:
            return self._parse(stream, fields)
        except (struct.error, LookupError, OverflowError):
            return {}

    def _parse(self, stream: bytes, fields: Mapping[int, PropertyName]) -> dict[str, str]:
        section = struct.unpack_from("<I", stream, self.FIRST_SECTION_OFFSET)[0]
        count = struct.unpack_from("<I", stream, section + 4)[0]
        pairs = struct.unpack_from(f"<{2 * count}I", stream, section + 8)
        ids, positions = pairs[::2], pairs[1::2]
        offsets = {pid: section + at for pid, at in zip(ids, positions, strict=True)}
        codec = self._codec(stream, offsets.get(self.CODEPAGE_ID))
        values = ((fields.get(pid), self._value(stream, at, codec)) for pid, at in offsets.items())
        return {name: value for name, value in values if name and value}

    def _codec(self, stream: bytes, offset: int | None) -> str:
        codepage = self.DEFAULT_CODEPAGE
        if offset is not None:
            codepage = struct.unpack_from("<H", stream, offset + 4)[0]
        return "utf-16-le" if codepage == self.UNICODE_CODEPAGE else f"cp{codepage}"

    def _value(self, stream: bytes, offset: int, codec: str) -> str:
        kind, size = struct.unpack_from("<II", stream, offset)
        if kind == self.VT_LPSTR:
            raw = stream[offset + 8 : offset + 8 + size]
            return raw.decode(codec, "replace").rstrip("\x00").strip()
        if kind == self.VT_LPWSTR:
            raw = stream[offset + 8 : offset + 8 + 2 * size]
            return raw.decode("utf-16-le", "replace").rstrip("\x00").strip()
        if kind == self.VT_FILETIME:
            return self._filetime(struct.unpack_from("<Q", stream, offset + 4)[0])
        return ""

    def _filetime(self, ticks: int) -> str:
        if ticks == 0:
            return ""
        moment = self.FILETIME_EPOCH + timedelta(microseconds=ticks // 10)
        return moment.strftime("%Y-%m-%dT%H:%M:%SZ")
