from enum import StrEnum


class BatchField(StrEnum):
    """Keys of a stored batch document."""

    BATCH_ID = "batch_id"
    FILES = "files"
    FILE_NAME = "file_name"
    JOB_ID = "job_id"
