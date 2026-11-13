from pathlib import Path

from ParserService.Domain.Documents.ParseOutcome import ParseOutcome
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.ArtifactPointer import ArtifactPointer
from ParserService.Domain.Jobs.FailureReason import FailureReason
from ParserService.Domain.Jobs.FileName import FileName
from ParserService.Infrastructure.Isolation.IsolatedParseRunner import IsolatedParseRunner
from ParserService.Infrastructure.Isolation.WorkerFile import WorkerFile


class IsolatedDocumentParser:
    """DocumentParser that parses stored files with the isolated worker process.

    It resolves pointers against the local artifact folder, which the worker reads
    directly, so the file's bytes never pass through the parent's memory.
    """

    def __init__(self, artifact_root: Path, runner: IsolatedParseRunner) -> None:
        self._artifact_root = artifact_root.resolve()
        self._runner = runner

    def parse(
        self, file_pointer: ArtifactPointer, file_name: FileName
    ) -> Result[ParseOutcome, FailureReason]:
        """Parse a stored file in isolation.

        Args:
            file_pointer: Where the original file is stored.
            file_name: The caller's file name.

        Returns:
            The outcome, or why the file could not be parsed.
        """
        source = self._artifact_root / file_pointer.key
        ran = self._runner.run(source, file_name)
        # A password is only kept until the worker has used it.
        (source.parent / WorkerFile.UNLOCK).unlink(missing_ok=True)
        if ran.is_err:
            return Result.err(ran.unwrap_err())
        return Result.ok(ran.unwrap().outcome)
