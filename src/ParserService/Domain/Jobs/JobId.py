import uuid
from dataclasses import dataclass
from typing import Self


@dataclass(frozen=True, slots=True)
class JobId:
    """Identifier of a parse job: a UUID in its canonical text form."""

    value: str

    def __post_init__(self) -> None:
        uuid.UUID(self.value)

    @classmethod
    def new(cls) -> Self:
        """Create a fresh, random job identifier.

        Returns:
            A job identifier that no other job shares.
        """
        return cls(str(uuid.uuid4()))

    def __str__(self) -> str:
        return self.value
