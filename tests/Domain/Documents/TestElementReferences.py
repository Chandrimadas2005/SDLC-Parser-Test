import pytest

from ParserService.Domain.Documents import Element, ElementId, ElementKind, ImageSource, Locator

LOCATOR = Locator.for_text(1, 0, 1)


class TestElementReferences:
    """Only links carry an href and only images carry an image source (schema 1.2)."""

    def test_a_link_keeps_its_href_and_an_image_its_source(self) -> None:
        link = Element(ElementId.at(1), ElementKind.LINK, LOCATOR, "x", href="/x")
        image = Element(ElementId.at(2), ElementKind.IMAGE, LOCATOR, image=ImageSource("a.png"))

        assert link.href == "/x"
        assert image.image == ImageSource("a.png", None, None)

    @pytest.mark.parametrize("href", ["", "   "])
    def test_a_blank_href_is_rejected(self, href: str) -> None:
        with pytest.raises(ValueError, match="href"):
            Element(ElementId.at(1), ElementKind.LINK, LOCATOR, href=href)

    def test_only_links_carry_an_href(self) -> None:
        with pytest.raises(ValueError, match="href"):
            Element(ElementId.at(1), ElementKind.PARAGRAPH, LOCATOR, "x", href="/x")

    def test_only_images_carry_an_image_source(self) -> None:
        with pytest.raises(ValueError, match="image source"):
            Element(ElementId.at(1), ElementKind.LINK, LOCATOR, image=ImageSource("a.png"))

    @pytest.mark.parametrize(
        ("source", "width", "height"), [(" ", None, None), (None, 0, None), (None, None, -1)]
    )
    def test_image_sources_are_validated(
        self, source: str | None, width: int | None, height: int | None
    ) -> None:
        with pytest.raises(ValueError, match="image"):
            ImageSource(source, width, height)
