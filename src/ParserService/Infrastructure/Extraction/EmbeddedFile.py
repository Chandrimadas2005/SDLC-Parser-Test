from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EmbeddedFile:
    """A file found inside another one: an archive entry or an e-mail attachment."""

    name: str
    content: bytes

    def __repr__(self) -> str:
        return f"EmbeddedFile(name={self.name!r}, size={len(self.content)})"
