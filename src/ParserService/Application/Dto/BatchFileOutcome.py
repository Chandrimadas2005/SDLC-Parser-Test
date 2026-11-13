from dataclasses import dataclass

from ParserService.Application.Dto.ParseJobSubmitted import ParseJobSubmitted
from ParserService.Application.Errors.ApplicationErrorCode import ApplicationErrorCode
from ParserService.Domain.Jobs.FileName import FileName


@dataclass(frozen=True, slots=True)
class BatchFileOutcome:
    """What happened to one file of a multi-file upload: its job, or why it was refused."""

    file_name: FileName
    submitted: ParseJobSubmitted | None
    error: ApplicationErrorCode | None
