from ParserService.Application.Errors.ApplicationErrorCode import ApplicationErrorCode


class ApiError(Exception):
    """Raised inside a route to answer with the error envelope for a known code.

    ``retry_after_seconds`` is only set for ``QUEUE_FULL`` and becomes the
    ``Retry-After`` header.
    """

    def __init__(self, code: ApplicationErrorCode, retry_after_seconds: int | None = None) -> None:
        super().__init__(code.value)
        self.code = code
        self.retry_after_seconds = retry_after_seconds
