from ParserService.Domain.Jobs.JobStatus import JobStatus


class InvalidJobTransitionError(Exception):
    """Raised when code asks a job to move in a way its status does not allow.

    This is a programming error, not an expected failure, so it is an exception and
    not a ``Result``.
    """

    def __init__(self, status: JobStatus, transition: str) -> None:
        super().__init__(f"cannot {transition} a job that is {status}")
        self.status = status
        self.transition = transition
