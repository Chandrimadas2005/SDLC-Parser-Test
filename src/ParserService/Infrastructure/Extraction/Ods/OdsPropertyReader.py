import zipfile
import zlib
from collections.abc import Mapping
from pathlib import Path
from typing import Final
from xml.etree.ElementTree import Element

from defusedxml import ElementTree

from ParserService.Domain.Documents.PropertyName import PropertyName
from ParserService.Infrastructure.Extraction.Ods.OdsName import OdsName


class OdsPropertyReader:
    """Reads an ODS package's own properties from ``meta.xml`` (brief, 2.2, file facts).

    Title, subject, creator, description, keywords, language, creation and change
    dates and the generating application go into ``DocumentFacts.properties``. A
    missing or unreadable ``meta.xml`` gives no properties; it never fails a parse.
    """

    META: Final = "meta.xml"
    KEYWORD_SEPARATOR: Final = ", "
    ERRORS: Final = (
        OSError,
        KeyError,
        EOFError,
        ValueError,
        zipfile.BadZipFile,
        zlib.error,
        ElementTree.ParseError,
    )
    FIELDS: Final[Mapping[OdsName, PropertyName]] = {
        OdsName.TITLE: PropertyName.TITLE,
        OdsName.SUBJECT: PropertyName.SUBJECT,
        OdsName.CREATOR: PropertyName.CREATOR,
        OdsName.DESCRIPTION: PropertyName.DESCRIPTION,
        OdsName.LANGUAGE: PropertyName.LANGUAGE,
        OdsName.CREATED: PropertyName.CREATED,
        OdsName.MODIFIED: PropertyName.MODIFIED,
        OdsName.GENERATOR: PropertyName.APPLICATION,
    }

    def read(self, path: Path) -> dict[str, str]:
        """Read the package properties.

        Args:
            path: The ODS file.

        Returns:
            The properties found, keyed by ``PropertyName``.
        """
        meta = self._meta(path)
        if meta is None:
            return {}
        found = {str(name): self._text(meta, tag) for tag, name in self.FIELDS.items()}
        keywords = [" ".join((node.text or "").split()) for node in meta.iter(OdsName.KEYWORD)]
        found[PropertyName.KEYWORDS] = self.KEYWORD_SEPARATOR.join(
            word for word in keywords if word
        )
        return {name: value for name, value in found.items() if value}

    def _meta(self, path: Path) -> Element | None:
        try:
            with zipfile.ZipFile(path) as archive:
                if self.META not in archive.namelist():
                    return None
                return ElementTree.fromstring(archive.read(self.META))
        except self.ERRORS:
            return None

    @staticmethod
    def _text(meta: Element, tag: OdsName) -> str:
        node = meta.find(f".//{tag}")
        return "" if node is None else " ".join((node.text or "").split())
