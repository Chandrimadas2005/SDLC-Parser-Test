from enum import StrEnum


class JobColumn(StrEnum):
    """Column names of the ``parser.jobs`` table (brief, section 2.7)."""

    ID = "id"
    FILE_HASH = "file_hash"
    PARSER_VERSION = "parser_version"
    FILE_NAME = "file_name"
    STATUS = "status"
    FAILURE_REASON = "failure_reason"
    ATTEMPT_COUNT = "attempt_count"
    FILE_POINTER = "file_pointer"
    RESULT_POINTER = "result_pointer"
    WARNING_COUNT = "warning_count"
    CREATED_AT = "created_at"
    STARTED_AT = "started_at"
    FINISHED_AT = "finished_at"
    DURATION_MS = "duration_ms"
