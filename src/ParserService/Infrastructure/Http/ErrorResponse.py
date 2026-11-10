from pydantic import BaseModel, ConfigDict

from ParserService.Application.Errors.ApplicationErrorCode import ApplicationErrorCode


class ErrorResponse(BaseModel):
    """The error envelope every failed call returns: code, message and request ID."""

    model_config = ConfigDict(frozen=True)

    code: ApplicationErrorCode
    message: str
    request_id: str
