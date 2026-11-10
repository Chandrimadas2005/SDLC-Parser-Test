from http import HTTPStatus

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from ParserService.Application.Errors.ApplicationErrorCode import ApplicationErrorCode
from ParserService.Infrastructure.Http.ApiError import ApiError
from ParserService.Infrastructure.Http.ErrorResponse import ErrorResponse
from ParserService.Infrastructure.Http.HttpHeader import HttpHeader
from ParserService.Infrastructure.Http.HttpStatusMapping import HttpStatusMapping
from ParserService.Infrastructure.Http.RequestIdMiddleware import RequestIdMiddleware
from ParserService.Infrastructure.Logging.LogField import LogField


class ErrorEnvelopeHandler:
    """Turns every error into the same envelope: code, message, request ID.

    Known codes come from ``ApiError``. Malformed requests become ``INVALID_REQUEST``.
    Anything unexpected is logged with context and answered as ``INTERNAL_ERROR``.
    """

    def __init__(self, mapping: HttpStatusMapping) -> None:
        self._mapping = mapping
        self._log = structlog.get_logger(__name__)

    def install(self, app: FastAPI) -> None:
        """Register the exception handlers on an application.

        Args:
            app: The FastAPI application to protect.
        """
        app.add_exception_handler(ApiError, self._handle_api_error)
        app.add_exception_handler(RequestValidationError, self._handle_validation_error)
        app.add_exception_handler(Exception, self._handle_unexpected)

    def envelope(self, request: Request, error: ApiError) -> JSONResponse:
        """Build the envelope response for a known error.

        Args:
            request: The failing request, used for its request ID.
            error: The error to report.

        Returns:
            A JSON response with the envelope body and status.
        """
        request_id = self.request_id(request)
        body = ErrorResponse(
            code=error.code, message=self._mapping.message(error.code), request_id=request_id
        )
        headers = {HttpHeader.REQUEST_ID.value: request_id}
        if error.retry_after_seconds is not None:
            headers[HttpHeader.RETRY_AFTER.value] = str(error.retry_after_seconds)
        status = self._mapping.status(error.code)
        return JSONResponse(body.model_dump(mode="json"), status_code=status, headers=headers)

    @staticmethod
    def request_id(request: Request) -> str:
        """Read the request ID the middleware stored.

        Args:
            request: The current request.

        Returns:
            The request ID, or an empty string when the middleware did not run.
        """
        return str(request.scope.get(RequestIdMiddleware.SCOPE_KEY, ""))

    async def _handle_api_error(self, request: Request, error: Exception) -> JSONResponse:
        if not isinstance(error, ApiError):
            raise error
        return self.envelope(request, error)

    async def _handle_validation_error(self, request: Request, error: Exception) -> JSONResponse:
        self._log.info("request_rejected", **{LogField.ERROR_CODE: type(error).__name__})
        return self.envelope(request, ApiError(ApplicationErrorCode.INVALID_REQUEST))

    async def _handle_unexpected(self, request: Request, error: Exception) -> JSONResponse:
        self._log.exception(
            "unhandled_error",
            **{
                LogField.HTTP_METHOD: request.method,
                LogField.HTTP_PATH: request.url.path,
                LogField.HTTP_STATUS: int(HTTPStatus.INTERNAL_SERVER_ERROR),
                LogField.ERROR_CODE: type(error).__name__,
            },
        )
        return self.envelope(request, ApiError(ApplicationErrorCode.INTERNAL_ERROR))
