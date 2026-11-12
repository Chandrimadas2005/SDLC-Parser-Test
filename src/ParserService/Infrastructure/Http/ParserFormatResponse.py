from pydantic import BaseModel, ConfigDict


class ParserFormatResponse(BaseModel):
    """Supported parser formats and the parser version serving them."""

    model_config = ConfigDict(frozen=True)

    parser_version: str
    formats: tuple[str, ...]
