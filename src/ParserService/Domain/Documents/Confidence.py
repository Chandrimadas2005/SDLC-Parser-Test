from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Confidence:
    """How sure a guess is, from 0.0 (not at all) to 1.0 (certain).

    Used for header-row detection and OCR (brief, sections 2.2 and 2.5).
    """

    value: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.value <= 1.0:
            message = "confidence must be between 0.0 and 1.0"
            raise ValueError(message)
