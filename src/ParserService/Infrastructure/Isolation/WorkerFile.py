from enum import StrEnum


class WorkerFile(StrEnum):
    """Files a parse worker process writes into its private output folder."""

    RESULT = "result.json"
    OUTCOME = "outcome.json"
    FAILURE = "failure.txt"
