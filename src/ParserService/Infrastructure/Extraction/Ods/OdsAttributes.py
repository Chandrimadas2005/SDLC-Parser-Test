from xml.etree.ElementTree import Element

from ParserService.Infrastructure.Extraction.Ods.OdsName import OdsName


class OdsAttributes:
    """Reads OpenDocument attributes from ElementTree elements."""

    def text(self, element: Element, name: OdsName) -> str:
        """Read an attribute.

        Args:
            element: The element.
            name: The qualified attribute name.

        Returns:
            The value, or an empty string when it is missing.
        """
        return element.get(name, "")

    def count(self, element: Element, name: OdsName, maximum: int) -> int:
        """Read a repeat or span count, which defaults to one.

        Args:
            element: The element.
            name: The qualified attribute name.
            maximum: The largest count to accept; larger counts are capped.

        Returns:
            The count, between one and ``maximum``.
        """
        value = self.text(element, name)
        return max(1, min(int(value), maximum)) if value.isdigit() else 1
