from enum import StrEnum


class ApplicationErrorCode(StrEnum):
    """Expected failures of use cases. The HTTP layer maps each one to a status code.

    Every API error carries one of these codes, a message and a request ID
    (brief, section 2.4).
    """

    JOB_NOT_FOUND = "job_not_found"
    RESULT_NOT_READY = "result_not_ready"
    RESULT_NOT_FOUND = "result_not_found"
    RETRY_NOT_ALLOWED = "retry_not_allowed"
    FILE_TOO_LARGE = "file_too_large"
    QUEUE_FULL = "queue_full"
    STORAGE_UNAVAILABLE = "storage_unavailable"
    INVALID_REQUEST = "invalid_request"
    NOT_READY = "not_ready"
    INTERNAL_ERROR = "internal_error"
