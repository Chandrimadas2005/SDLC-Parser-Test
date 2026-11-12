from collections.abc import Mapping
from http import HTTPStatus
from typing import ClassVar

from ParserService.Application.Errors.ApplicationErrorCode import ApplicationErrorCode


class HttpStatusMapping:
    """Which HTTP status and message each application error code maps to."""

    STATUSES: ClassVar[Mapping[ApplicationErrorCode, HTTPStatus]] = {
        ApplicationErrorCode.JOB_NOT_FOUND: HTTPStatus.NOT_FOUND,
        ApplicationErrorCode.RESULT_NOT_FOUND: HTTPStatus.NOT_FOUND,
        ApplicationErrorCode.RESULT_NOT_READY: HTTPStatus.CONFLICT,
        ApplicationErrorCode.RETRY_NOT_ALLOWED: HTTPStatus.CONFLICT,
        ApplicationErrorCode.FILE_TOO_LARGE: HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
        ApplicationErrorCode.DISK_FULL: HTTPStatus.SERVICE_UNAVAILABLE,
        ApplicationErrorCode.QUEUE_FULL: HTTPStatus.TOO_MANY_REQUESTS,
        ApplicationErrorCode.STORAGE_UNAVAILABLE: HTTPStatus.SERVICE_UNAVAILABLE,
        ApplicationErrorCode.INVALID_REQUEST: HTTPStatus.BAD_REQUEST,
        ApplicationErrorCode.NOT_READY: HTTPStatus.SERVICE_UNAVAILABLE,
        ApplicationErrorCode.INTERNAL_ERROR: HTTPStatus.INTERNAL_SERVER_ERROR,
    }
    MESSAGES: ClassVar[Mapping[ApplicationErrorCode, str]] = {
        ApplicationErrorCode.JOB_NOT_FOUND: "No parse job has this identifier.",
        ApplicationErrorCode.RESULT_NOT_FOUND: "The stored parse result is missing.",
        ApplicationErrorCode.RESULT_NOT_READY: "The parse result is not ready yet.",
        ApplicationErrorCode.RETRY_NOT_ALLOWED: "Only failed parse jobs can be retried.",
        ApplicationErrorCode.FILE_TOO_LARGE: "The file exceeds the configured size limit.",
        ApplicationErrorCode.DISK_FULL: (
            "Uploads are disabled because the artifact disk is nearly full."
        ),
        ApplicationErrorCode.QUEUE_FULL: "The parse queue is full; retry after the given delay.",
        ApplicationErrorCode.STORAGE_UNAVAILABLE: "Storage is temporarily unavailable.",
        ApplicationErrorCode.INVALID_REQUEST: "The request is malformed.",
        ApplicationErrorCode.NOT_READY: "The service is not ready to accept work.",
        ApplicationErrorCode.INTERNAL_ERROR: "An unexpected error occurred.",
    }

    def status(self, code: ApplicationErrorCode) -> HTTPStatus:
        """Look up the HTTP status for an error code.

        Args:
            code: The application error code.

        Returns:
            The HTTP status to answer with.
        """
        return self.STATUSES[code]

    def message(self, code: ApplicationErrorCode) -> str:
        """Look up the caller-facing message for an error code.

        Args:
            code: The application error code.

        Returns:
            A short, content-free explanation.
        """
        return self.MESSAGES[code]
