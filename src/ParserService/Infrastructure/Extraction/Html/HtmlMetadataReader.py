from dataclasses import replace
from typing import Final

from bs4 import BeautifulSoup
from bs4.element import Tag

from ParserService.Domain.Documents.DocumentFacts import DocumentFacts
from ParserService.Infrastructure.Extraction.Html.HtmlAttribute import HtmlAttribute
from ParserService.Infrastructure.Extraction.Html.HtmlProperty import HtmlProperty
from ParserService.Infrastructure.Extraction.Html.HtmlTag import HtmlTag


class HtmlMetadataReader:
    """Adds an HTML document's own metadata to its file facts (brief, 2.2, file facts).

    The ``<title>`` and the author, description and keywords ``<meta>`` entries go
    into ``properties``; the ``lang`` attribute of ``<html>`` becomes the language.
    Missing entries are left out.
    """

    META_PROPERTIES: Final = (HtmlProperty.AUTHOR, HtmlProperty.DESCRIPTION, HtmlProperty.KEYWORDS)

    def facts(self, facts: DocumentFacts, soup: BeautifulSoup) -> DocumentFacts:
        """Add the document's metadata to its facts.

        Args:
            facts: The facts computed from the file.
            soup: The parsed document.

        Returns:
            The facts with the language and properties filled in.
        """
        properties = {**(facts.properties or {}), **self._properties(soup)}
        language = self._language(soup) or facts.language
        return replace(facts, language=language, properties=properties)

    @staticmethod
    def _language(soup: BeautifulSoup) -> str:
        root = soup.find(HtmlTag.HTML)
        return HtmlAttribute.LANG.of(root) if isinstance(root, Tag) else ""

    def _properties(self, soup: BeautifulSoup) -> dict[str, str]:
        found = {HtmlProperty.TITLE: self._title(soup)}
        found |= {name: self._meta(soup, name) for name in self.META_PROPERTIES}
        return {str(name): value for name, value in found.items() if value}

    @staticmethod
    def _title(soup: BeautifulSoup) -> str:
        title = soup.find(HtmlTag.TITLE)
        return " ".join(title.get_text().split()) if isinstance(title, Tag) else ""

    @staticmethod
    def _meta(soup: BeautifulSoup, name: HtmlProperty) -> str:
        meta = soup.find(HtmlTag.META, attrs={HtmlAttribute.NAME: name.value})
        return HtmlAttribute.CONTENT.of(meta) if isinstance(meta, Tag) else ""
