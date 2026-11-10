from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ArtifactPointer:
    """Location of a stored artifact (original file or result) inside the ArtifactStore.

    The key is a relative, forward-slash path that is opaque to the Domain; only the
    store knows how to resolve it. It can never climb out of the store's root.
    """

    key: str

    def __post_init__(self) -> None:
        if not self.key or self.key != self.key.strip() or "\\" in self.key:
            message = "artifact key must be a non-blank path without backslashes"
            raise ValueError(message)
        if self.key.startswith("/") or ".." in self.key.split("/"):
            message = "artifact key must be relative and must not climb directories"
            raise ValueError(message)

    def __str__(self) -> str:
        return self.key
