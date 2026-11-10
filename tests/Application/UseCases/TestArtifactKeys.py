import pytest

from ParserService.Application.UseCases import ArtifactKeys, SubmitPolicy
from ParserService.Domain.Jobs import FileHash, FileName, ParserVersion

HASH = FileHash("c" * 64)
VERSION = ParserVersion("0.1.0")


class TestArtifactKeys:
    """Pointers are derived from the hash and version, never from the file name."""

    def test_original_file_keeps_only_the_extension(self) -> None:
        pointer = ArtifactKeys().original_file(HASH, FileName("Customer List.XLSX"))

        assert pointer.key == f"files/cc/{'c' * 64}/original.xlsx"

    def test_original_file_without_extension(self) -> None:
        assert ArtifactKeys().original_file(HASH, FileName("README")).key.endswith("/original")
        assert str(FileName("README")) == "README"

    def test_submit_policy_requires_a_positive_size_limit(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            SubmitPolicy(VERSION, 0)

    def test_results_are_keyed_by_hash_and_parser_version(self) -> None:
        keys = ArtifactKeys()

        assert keys.result_json(HASH, VERSION).key == f"results/cc/{'c' * 64}/0.1.0/result.json"
        assert keys.result_markdown(HASH, VERSION).key == f"results/cc/{'c' * 64}/0.1.0/result.md"
