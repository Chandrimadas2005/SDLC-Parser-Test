from typing import Final

from ParserService.Domain.Jobs.ArtifactPointer import ArtifactPointer
from ParserService.Domain.Jobs.FileHash import FileHash
from ParserService.Domain.Jobs.FileName import FileName
from ParserService.Domain.Jobs.ParserVersion import ParserVersion


class ArtifactKeys:
    """Builds the pointers under which files and results are stored.

    Keys are derived from the file hash, never from the caller's file name, so two
    uploads of the same bytes share one stored copy and no name leaks into storage.
    """

    FILES_PREFIX: Final = "files"
    RESULTS_PREFIX: Final = "results"
    ORIGINAL_STEM: Final = "original"
    FAN_OUT: Final = 2

    def original_file(self, file_hash: FileHash, file_name: FileName) -> ArtifactPointer:
        """Where the uploaded bytes live; the extension is kept as a detection hint.

        Args:
            file_hash: Digest of the uploaded bytes.
            file_name: The caller's file name; only its extension is used.

        Returns:
            Pointer to the original file.
        """
        stem = f"{self.ORIGINAL_STEM}{file_name.extension}"
        return ArtifactPointer(f"{self.FILES_PREFIX}/{self._shard(file_hash)}/{stem}")

    def result_json(self, file_hash: FileHash, version: ParserVersion) -> ArtifactPointer:
        """Where the JSON ``ParsedDocument`` for a file and parser version lives.

        Args:
            file_hash: Digest of the parsed file.
            version: Parser version that produced the result.

        Returns:
            Pointer to the JSON result.
        """
        return ArtifactPointer(f"{self._result_base(file_hash, version)}.json")

    def result_markdown(self, file_hash: FileHash, version: ParserVersion) -> ArtifactPointer:
        """Where the Markdown rendering for a file and parser version lives.

        Args:
            file_hash: Digest of the parsed file.
            version: Parser version that produced the result.

        Returns:
            Pointer to the Markdown result.
        """
        return ArtifactPointer(f"{self._result_base(file_hash, version)}.md")

    def _result_base(self, file_hash: FileHash, version: ParserVersion) -> str:
        return f"{self.RESULTS_PREFIX}/{self._shard(file_hash)}/{version}/result"

    def _shard(self, file_hash: FileHash) -> str:
        return f"{file_hash.value[: self.FAN_OUT]}/{file_hash.value}"
