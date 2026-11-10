from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Self

from ParserService.Domain.Documents.Element import Element
from ParserService.Domain.Documents.ElementKind import ElementKind
from ParserService.Domain.Documents.MetricName import MetricName


@dataclass(frozen=True, slots=True)
class Metrics:
    """Counts for the whole file (brief, section 2.2).

    ``counts`` holds the format-level counts, such as words or rows.
    ``elements_by_kind`` holds how many elements of each kind were extracted.
    """

    counts: Mapping[MetricName, int]
    elements_by_kind: Mapping[ElementKind, int]

    def __post_init__(self) -> None:
        values = [*self.counts.values(), *self.elements_by_kind.values()]
        if any(value < 0 for value in values):
            message = "counts cannot be negative"
            raise ValueError(message)

    @classmethod
    def for_elements(cls, elements: Sequence[Element], counts: Mapping[MetricName, int]) -> Self:
        """Build metrics, counting the elements by kind.

        Args:
            elements: Every extracted element.
            counts: The format-level counts.

        Returns:
            Metrics holding both.
        """
        by_kind = Counter(element.kind for element in elements)
        ordered = {kind: by_kind[kind] for kind in ElementKind if by_kind[kind]}
        return cls(counts=counts, elements_by_kind=ordered)
