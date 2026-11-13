from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExtractionContext:
    """Per-file details that change how extractors are built.

    ``password`` opens an encrypted PDF; ``archive_depth`` says how deep inside
    archives or e-mails the file sits, so nested archives can be capped.
    """

    password: str | None = None
    archive_depth: int = 0

    def __repr__(self) -> str:
        return f"ExtractionContext(archive_depth={self.archive_depth}, password=...)"
