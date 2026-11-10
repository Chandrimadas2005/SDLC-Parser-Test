"""Domain errors: the Result type for expected failures and the error codes it carries."""

from ParserService.Domain.Errors.JobQueueError import JobQueueError
from ParserService.Domain.Errors.JobRepositoryError import JobRepositoryError
from ParserService.Domain.Errors.Result import Result

__all__ = ["JobQueueError", "JobRepositoryError", "Result"]
