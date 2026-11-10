from enum import StrEnum


class HttpHeader(StrEnum):
    """HTTP header names the service reads or writes."""

    REQUEST_ID = "X-Request-ID"
    RETRY_AFTER = "Retry-After"
    LOCATION = "Location"
    CONTENT_TYPE = "Content-Type"
