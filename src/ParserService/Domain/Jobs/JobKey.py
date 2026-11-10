from dataclasses import dataclass

from ParserService.Domain.Jobs.FileHash import FileHash
from ParserService.Domain.Jobs.ParserVersion import ParserVersion


@dataclass(frozen=True, slots=True)
class JobKey:
    """What makes a job unique: the same file parsed by the same parser version.

    A repeated upload with the same key returns the existing job instead of a new one.
    """

    file_hash: FileHash
    parser_version: ParserVersion
