from enum import StrEnum


class LogField(StrEnum):
    """Keys that may appear in log events. Identifiers, sizes, counts and timings only.

    Document content, file names chosen by customers and passwords never appear here.
    """

    REQUEST_ID = "request_id"
    JOB_ID = "job_id"
    FILE_HASH = "file_hash"
    STATUS = "status"
    ERROR_CODE = "error_code"
    SIZE_BYTES = "size_bytes"
    DURATION_MS = "duration_ms"
    HTTP_METHOD = "http_method"
    HTTP_PATH = "http_path"
    HTTP_STATUS = "http_status"
    QUEUE_DEPTH = "queue_depth"
