from enum import StrEnum


class WorkerFile(StrEnum):
    """Files a parse worker process reads or writes.

    ``UNLOCK`` holds the caller's password and sits next to the stored original
    (see ArtifactKeys.password); the others go into the worker's output folder.
    """

    UNLOCK = "unlock"
    RESULT = "result.json"
    OUTCOME = "outcome.json"
    FAILURE = "failure.txt"
