from fastapi import APIRouter

from ParserService.Infrastructure.Extraction.ExtractorRegistry import ExtractorRegistry
from ParserService.Infrastructure.Http.ParserFormatResponse import ParserFormatResponse


class FormatsRouter:
    """Expose the registered formats and parser version at ``GET /v1/formats``."""

    def __init__(self, registry: ExtractorRegistry, parser_version: str) -> None:
        self._registry = registry
        self._parser_version = parser_version
        self.router = APIRouter(prefix="/v1")
        self.router.add_api_route(
            "/formats",
            self.formats,
            methods=["GET"],
            response_model=ParserFormatResponse,
            summary="List supported formats",
            description="Returns registered file formats and parser version.",
        )

    async def formats(self) -> ParserFormatResponse:
        """Return only formats with a registered extractor."""
        supported = tuple(kind.value for kind in self._registry.supported_types)
        return ParserFormatResponse(parser_version=self._parser_version, formats=supported)
