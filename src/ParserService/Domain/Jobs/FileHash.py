import hashlib
from dataclasses import dataclass
from typing import ClassVar, Self


@dataclass(frozen=True, slots=True)
class FileHash:
    """SHA-256 digest of a submitted file, as 64 lower-case hexadecimal characters."""

    HEX_LENGTH: ClassVar[int] = 64
    HEX_DIGITS: ClassVar[frozenset[str]] = frozenset("0123456789abcdef")

    value: str

    def __post_init__(self) -> None:
        if len(self.value) != self.HEX_LENGTH or not self.HEX_DIGITS.issuperset(self.value):
            message = f"file hash must be {self.HEX_LENGTH} lower-case hex characters"
            raise ValueError(message)

    @classmethod
    def of(cls, content: bytes) -> Self:
        """Compute the digest of file content held in memory.

        Args:
            content: The bytes of the file.

        Returns:
            The SHA-256 digest of the content.
        """
        return cls(hashlib.sha256(content).hexdigest())

    def __str__(self) -> str:
        return self.value
