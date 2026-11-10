import pytest

from ParserService.Domain.Jobs import (
    ArtifactPointer,
    Duration,
    FileHash,
    FileName,
    Instant,
    JobCompletion,
    JobId,
    JobStatus,
    ParserVersion,
)


class TestValueObjects:
    """Value objects validate on construction and compare by value."""

    def test_job_id_is_a_uuid_and_new_ids_differ(self) -> None:
        first, second = JobId.new(), JobId.new()

        assert first != second
        assert str(first) == first.value
        with pytest.raises(ValueError, match="badly formed"):
            JobId("not-a-uuid")

    def test_file_hash_is_computed_and_validated(self) -> None:
        digest = FileHash.of(b"hello")

        assert str(digest) == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
        assert digest == FileHash(digest.value)

    @pytest.mark.parametrize("value", ["abc", "A" * 64, "g" * 64])
    def test_file_hash_rejects_wrong_length_or_characters(self, value: str) -> None:
        with pytest.raises(ValueError, match="hex characters"):
            FileHash(value)

    @pytest.mark.parametrize("value", ["", " ", "a/b", "a\\b", ".", "..", "x" * 256])
    def test_file_name_rejects_paths_and_blank_names(self, value: str) -> None:
        with pytest.raises(ValueError, match="file name"):
            FileName(value)

    def test_file_name_extension_is_a_lower_case_hint(self) -> None:
        assert FileName("Report.XLSX").extension == ".xlsx"
        assert FileName("README").extension == ""
        assert FileName(".bashrc").extension == ""

    def test_parser_version_must_not_be_blank(self) -> None:
        assert str(ParserVersion("1.2.3")) == "1.2.3"
        with pytest.raises(ValueError, match="blank"):
            ParserVersion("   ")

    @pytest.mark.parametrize("key", ["", " a", "a\\b", "/abs", "a/../b"])
    def test_artifact_pointer_rejects_unsafe_keys(self, key: str) -> None:
        with pytest.raises(ValueError, match="artifact key"):
            ArtifactPointer(key)

    def test_artifact_pointer_accepts_relative_keys(self) -> None:
        assert str(ArtifactPointer("files/ab/abcd.bin")) == "files/ab/abcd.bin"

    def test_instant_and_duration_reject_negative_values(self) -> None:
        assert Instant(1_000).until(Instant(1_250)) == Duration(250)
        assert Instant(1) < Instant(2)
        with pytest.raises(ValueError, match="epoch"):
            Instant(-1)
        with pytest.raises(ValueError, match="negative"):
            Duration(-1)

    def test_job_status_terminal_states(self) -> None:
        assert JobStatus.SUCCEEDED.is_terminal
        assert JobStatus.FAILED.is_terminal
        assert not JobStatus.QUEUED.is_terminal
        assert not JobStatus.RUNNING.is_terminal

    def test_job_completion_validates_status_and_warning_count(self) -> None:
        pointer = ArtifactPointer("results/x.json")

        with pytest.raises(ValueError, match="succeeded or partial"):
            JobCompletion(JobStatus.FAILED, pointer, 0)
        with pytest.raises(ValueError, match="negative"):
            JobCompletion(JobStatus.SUCCEEDED, pointer, -1)
