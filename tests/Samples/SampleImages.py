import io
import struct
import zlib
from pathlib import Path
from typing import Final

import pypdfium2
from reportlab.pdfgen import canvas


class SampleImages:
    """Writes synthetic PNG images of printed text, without any imaging library.

    The text is drawn into a PDF with reportlab, rendered to grayscale pixels with
    PDFium, and encoded as PNG by hand (signature, IHDR, IDAT, IEND).
    """

    SIZE: Final = (595, 300)
    SCALE: Final = 3.0

    def text(self, path: Path, lines: tuple[str, ...]) -> Path:
        """An image with the given lines of large, clear text."""
        buffer = io.BytesIO()
        page = canvas.Canvas(buffer, pagesize=self.SIZE)
        page.setFont("Helvetica", 26)
        for index, line in enumerate(lines):
            page.drawString(40, 240 - index * 50, line)
        page.save()
        return self._png(path, buffer.getvalue())

    def blank(self, path: Path) -> Path:
        """A white image with no text."""
        return self.text(path, (" ",))

    def _png(self, path: Path, pdf: bytes) -> Path:
        bitmap = pypdfium2.PdfDocument(pdf)[0].render(scale=self.SCALE, grayscale=True)
        width, height, stride = bitmap.width, bitmap.height, bitmap.stride
        pixels = bytes(bitmap.buffer)
        raw = b"".join(
            b"\x00" + pixels[row * stride : row * stride + width] for row in range(height)
        )
        header = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
        chunks = [self._chunk(b"IHDR", header), self._chunk(b"IDAT", zlib.compress(raw))]
        path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"".join(chunks) + self._chunk(b"IEND", b""))
        return path

    @staticmethod
    def _chunk(kind: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(kind + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", crc)
