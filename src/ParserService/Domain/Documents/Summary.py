from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Summary:
    """A short text summary of one parsed document (brief, section 2.2, optional summary).

    A summary is kept beside the ``ParsedDocument``, never inside it, so the output
    schema does not change when summaries are switched on.
    """

    text: str

    def __post_init__(self) -> None:
        if not self.text.strip():
            message = "summary text must not be blank"
            raise ValueError(message)
