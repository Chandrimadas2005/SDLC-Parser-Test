import zipfile
from collections.abc import Mapping
from pathlib import Path
from typing import Final
from xml.etree import ElementTree

from ParserService.Domain.Documents import PropertyName


class XlsxPropertyReader:
    """Reads an XLSX or XLSM workbook's own metadata (brief, section 2.2, file properties).

    Core properties (title, author, dates) live in ``docProps/core.xml`` and extended
    properties (application, company, manager) in ``docProps/app.xml``. Both parts are
    small and optional; a missing or unreadable part simply adds no properties. Dates
    are kept exactly as the file stores them (ISO 8601).
    """

    CORE_PART: Final = "docProps/core.xml"
    APP_PART: Final = "docProps/app.xml"
    CORE_FIELDS: Final[Mapping[str, PropertyName]] = {
        "title": PropertyName.TITLE,
        "subject": PropertyName.SUBJECT,
        "creator": PropertyName.CREATOR,
        "keywords": PropertyName.KEYWORDS,
        "description": PropertyName.DESCRIPTION,
        "category": PropertyName.CATEGORY,
        "contentStatus": PropertyName.CONTENT_STATUS,
        "identifier": PropertyName.IDENTIFIER,
        "language": PropertyName.LANGUAGE,
        "version": PropertyName.VERSION,
        "revision": PropertyName.REVISION,
        "lastModifiedBy": PropertyName.LAST_MODIFIED_BY,
        "created": PropertyName.CREATED,
        "modified": PropertyName.MODIFIED,
        "lastPrinted": PropertyName.LAST_PRINTED,
    }
    APP_FIELDS: Final[Mapping[str, PropertyName]] = {
        "Application": PropertyName.APPLICATION,
        "AppVersion": PropertyName.APP_VERSION,
        "Company": PropertyName.COMPANY,
        "Manager": PropertyName.MANAGER,
    }

    def read(self, path: Path) -> dict[str, str]:
        """Read the workbook's core and extended properties.

        Args:
            path: The workbook file.

        Returns:
            Non-empty property values keyed by ``PropertyName``.
        """
        with zipfile.ZipFile(path) as archive:
            app = self._part(archive, self.APP_PART, self.APP_FIELDS)
            core = self._part(archive, self.CORE_PART, self.CORE_FIELDS)
        return {**app, **core}

    def _part(
        self, archive: zipfile.ZipFile, name: str, fields: Mapping[str, PropertyName]
    ) -> dict[str, str]:
        root = self._root(archive, name)
        if root is None:
            return {}
        pairs = ((fields.get(node.tag.rpartition("}")[2]), node.text) for node in root)
        return {field: text.strip() for field, text in pairs if field and text and text.strip()}

    @staticmethod
    def _root(archive: zipfile.ZipFile, name: str) -> ElementTree.Element | None:
        if name not in archive.namelist():
            return None
        try:
            # Same stdlib parser XlsxExtractor uses; moving to defusedxml is an open point.
            return ElementTree.fromstring(archive.read(name))  # noqa: S314
        except ElementTree.ParseError:
            return None
