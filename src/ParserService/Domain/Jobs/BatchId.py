import uuid
from dataclasses import dataclass
from typing import Self


@dataclass(frozen=True, slots=True)
class BatchId:
    """Identifier of a multi-file upload: a UUID in its canonical text form."""

    value: str

    def __post_init__(self) -> None:
        uuid.UUID(self.value)

    @classmethod
    def new(cls) -> Self:
        """Create a fresh, random batch identifier.

        Returns:
            A batch identifier that no other batch shares.
        """
        return cls(str(uuid.uuid4()))

    def __str__(self) -> str:
        return self.value
