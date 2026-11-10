from dataclasses import dataclass
from typing import ClassVar, Self


@dataclass(frozen=True, slots=True)
class ElementId:
    """Stable identifier of an element, such as ``e-000001``.

    The id is derived from the element's position in reading order, so the same
    file and parser version always give the same ids (brief, section 2.3).
    """

    PREFIX: ClassVar[str] = "e-"
    MIN_DIGITS: ClassVar[int] = 6
    DIGITS: ClassVar[frozenset[str]] = frozenset("0123456789")

    value: str

    def __post_init__(self) -> None:
        number = self.value.removeprefix(self.PREFIX)
        well_formed = len(number) >= self.MIN_DIGITS and self.DIGITS.issuperset(number)
        if not self.value.startswith(self.PREFIX) or not well_formed:
            message = f"element id must be '{self.PREFIX}' and at least {self.MIN_DIGITS} digits"
            raise ValueError(message)

    @classmethod
    def at(cls, position: int) -> Self:
        """Build the id of the element at a position in reading order.

        Args:
            position: One-based position of the element in the document.

        Returns:
            The element id for that position.

        Raises:
            ValueError: If the position is below one.
        """
        if position < 1:
            message = "element position starts at 1"
            raise ValueError(message)
        return cls(f"{cls.PREFIX}{position:0{cls.MIN_DIGITS}d}")

    def __str__(self) -> str:
        return self.value
