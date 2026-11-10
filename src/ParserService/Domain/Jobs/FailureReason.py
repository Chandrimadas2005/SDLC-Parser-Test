from enum import StrEnum


class FailureReason(StrEnum):
    """The fixed set of reasons a job can fail (brief, sections 2.1 and 2.5)."""

    UNSUPPORTED_TYPE = "unsupported_type"
    CORRUPTED_FILE = "corrupted_file"
    PASSWORD_PROTECTED = "password_protected"  # noqa: S105 - a reason code, not a secret
    FILE_TOO_LARGE = "file_too_large"
    LIMIT_EXCEEDED = "limit_exceeded"
    TIMEOUT = "timeout"
    EXTRACTOR_CRASH = "extractor_crash"
    MAX_ATTEMPTS_EXCEEDED = "max_attempts_exceeded"
    STORAGE_ERROR = "storage_error"
