import struct
import zipfile
import zlib
from collections.abc import Iterator
from pathlib import Path
from typing import ClassVar, Final

from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.FailureReason import FailureReason


class ZipSalvager:
    """Rebuilds a ZIP-based file (DOCX, PPTX, XLSX) whose table of contents is damaged.

    Every entry in a ZIP also has its own local header, so entries can be recovered
    one by one by walking those headers from the start of the file, which is what an
    interrupted download or a damaged end usually leaves intact. Expansion is capped
    (entry count and total bytes) so a crafted file cannot exhaust memory.
    """

    MAX_ENTRIES: ClassVar[int] = 10_000
    MAX_EXPANDED_BYTES: ClassVar[int] = 512 * 1024 * 1024
    SIGNATURE: Final = b"PK\x03\x04"
    HEADER: Final = struct.Struct("<4sHHHHHIIIHH")
    STORED: Final = 0
    DEFLATED: Final = 8

    def salvage(self, source: Path, target: Path) -> Result[int, FailureReason]:
        """Recover the entries of a damaged archive into a new, valid one.

        Args:
            source: The damaged file.
            target: Where to write the rebuilt archive.

        Returns:
            How many entries were recovered, ``corrupted_file`` when none were, or
            ``limit_exceeded`` when the content expands beyond the caps.
        """
        entries = list(self._entries(source.read_bytes()))
        if not entries:
            return Result.err(FailureReason.CORRUPTED_FILE)
        if None in entries:
            return Result.err(FailureReason.LIMIT_EXCEEDED)
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as rebuilt:
            for name, content in (entry for entry in entries if entry is not None):
                rebuilt.writestr(name, content)
        return Result.ok(len(entries))

    def _entries(self, data: bytes) -> Iterator[tuple[str, bytes] | None]:
        offset, budget = data.find(self.SIGNATURE), self.MAX_EXPANDED_BYTES
        for _ in range(self.MAX_ENTRIES):
            entry = self._entry(data, offset, budget) if offset >= 0 else None
            if entry is None:
                return
            name, content, end = entry
            budget -= len(content)
            yield (name, content) if budget >= 0 else None
            offset = data.find(self.SIGNATURE, end)

    def _entry(self, data: bytes, offset: int, budget: int) -> tuple[str, bytes, int] | None:
        if offset + self.HEADER.size > len(data):
            return None
        fields = self.HEADER.unpack_from(data, offset)
        method, size, name_length, extra_length = fields[3], fields[7], fields[9], fields[10]
        start = offset + self.HEADER.size + name_length + extra_length
        name = data[offset + self.HEADER.size : offset + self.HEADER.size + name_length]
        content = self._content(data[start:], method, (size, budget + 1))
        if content is None:
            return None
        return name.decode("utf-8", "replace"), content[0], start + content[1]

    def _content(
        self, body: bytes, method: int, sizes: tuple[int, int]
    ) -> tuple[bytes, int] | None:
        stored_size, max_length = sizes
        if method == self.STORED:
            return body[:stored_size], stored_size
        if method != self.DEFLATED:
            return None
        inflater = zlib.decompressobj(-zlib.MAX_WBITS)
        try:
            content = inflater.decompress(body, max_length)
        except zlib.error:
            return None
        return content, len(body) - len(inflater.unused_data) - len(inflater.unconsumed_tail)
