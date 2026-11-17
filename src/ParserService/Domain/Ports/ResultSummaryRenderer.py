from typing import Protocol


class ResultSummaryRenderer(Protocol):
    """Builds a short summary of a stored JSON result."""

    def render(self, content: bytes) -> str:
        """Summarise a stored result.

        Args:
            content: The JSON result artifact, as stored by the worker.

        Returns:
            A short plain-text summary.
        """
