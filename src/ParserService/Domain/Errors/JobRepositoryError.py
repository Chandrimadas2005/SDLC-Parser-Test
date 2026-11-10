from enum import StrEnum


class JobRepositoryError(StrEnum):
    """Expected reasons a job record cannot be written."""

    DUPLICATE_KEY = "duplicate_key"
    NOT_FOUND = "not_found"
    STORE_UNAVAILABLE = "store_unavailable"
