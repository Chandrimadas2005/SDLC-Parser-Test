from dataclasses import dataclass

from ParserService.Application.Dto.ParseJobStatusView import ParseJobStatusView
from ParserService.Domain.Jobs.FileName import FileName


@dataclass(frozen=True, slots=True)
class BatchFileView:
    """One file of a batch: its job's status and, when asked for and ready, its result."""

    file_name: FileName
    status: ParseJobStatusView
    result: bytes | None
