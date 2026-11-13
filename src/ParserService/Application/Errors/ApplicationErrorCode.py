from enum import StrEnum


class ApplicationErrorCode(StrEnum):
    """Expected failures of use cases. The HTTP layer maps each one to a status code.

    Every API error carries one of these codes, a message and a request ID
    (brief, section 2.4).
    """

    JOB_NOT_FOUND = "job_not_found"
    BATCH_NOT_FOUND = "batch_not_found"
    BATCH_TOO_LARGE = "batch_too_large"
    RESULT_NOT_READY = "result_not_ready"
    RESULT_NOT_FOUND = "result_not_found"
    RETRY_NOT_ALLOWED = "retry_not_allowed"
    FILE_TOO_LARGE = "file_too_large"
    DISK_FULL = "disk_full"
    QUEUE_FULL = "queue_full"
    STORAGE_UNAVAILABLE = "storage_unavailable"
    INVALID_REQUEST = "invalid_request"
    NOT_READY = "not_ready"
    INTERNAL_ERROR = "internal_error"
