from dataclasses import dataclass

from ParserService.Domain.Ports.DiskSpace import DiskSpace
from ParserService.Domain.Ports.TemporaryFileCleaner import TemporaryFileCleaner


@dataclass(frozen=True, slots=True)
class DiskGuard:
    """Disk-capacity check and safe temporary-file cleanup collaborators."""

    disk_space: DiskSpace
    temporary_file_cleaner: TemporaryFileCleaner
