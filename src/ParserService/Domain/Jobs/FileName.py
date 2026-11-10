from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True, slots=True)
class FileName:
    """The name the caller gave the uploaded file: a plain base name, never a path.

    The extension is only a hint for type detection (brief, section 2.1).
    """

    MAX_LENGTH: ClassVar[int] = 255

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip() or len(self.value) > self.MAX_LENGTH:
            message = f"file name must be 1 to {self.MAX_LENGTH} characters"
            raise ValueError(message)
        if "/" in self.value or "\\" in self.value or self.value in {".", ".."}:
            message = "file name must be a base name without directory parts"
            raise ValueError(message)

    @property
    def extension(self) -> str:
        """The lower-case extension including the dot, or an empty string."""
        stem, dot, suffix = self.value.rpartition(".")
        return f".{suffix.lower()}" if stem and dot else ""

    def __str__(self) -> str:
        return self.value
