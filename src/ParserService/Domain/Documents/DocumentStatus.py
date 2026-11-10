from enum import StrEnum


class DocumentStatus(StrEnum):
    """Overall outcome of one parse (brief, section 2.3).

    ``PARTIAL`` means some parts could not be read; the warnings then say exactly
    what is missing. ``FAILED`` means nothing usable was produced and a failure
    reason is given.
    """

    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    FAILED = "failed"
