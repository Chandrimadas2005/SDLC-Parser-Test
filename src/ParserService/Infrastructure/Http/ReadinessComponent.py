from enum import StrEnum


class ReadinessComponent(StrEnum):
    """Things that must be healthy before the service accepts work."""

    DATABASE = "database"
    DISK = "disk"
