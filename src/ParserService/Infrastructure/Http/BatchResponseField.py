from enum import StrEnum


class BatchResponseField(StrEnum):
    """JSON keys of the multi-file upload responses."""

    BATCH_ID = "batch_id"
    STATUS = "status"
    FILES = "files"
    FILE_NAME = "file_name"
    JOB_ID = "job_id"
    ALREADY_EXISTED = "already_existed"
    ERROR = "error"
    FAILURE_REASON = "failure_reason"
    RESULT = "result"
