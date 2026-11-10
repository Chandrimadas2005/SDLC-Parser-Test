from pathlib import Path

import pytest

from ParserService.Domain.Jobs import ArtifactPointer
from ParserService.Infrastructure.Storage import LocalFileSystemArtifactStore

POINTER = ArtifactPointer("files/ab/abcdef/original.txt")


class TestLocalFileSystemArtifactStore:
    """Artifacts land below the root, writes are atomic, and deletes prune empty folders."""

    def test_put_then_read_round_trips(self, tmp_path: Path) -> None:
        store = LocalFileSystemArtifactStore(tmp_path / "artifacts")

        store.put(POINTER, b"hello")

        assert store.read(POINTER) == b"hello"
        assert store.exists(POINTER)
        assert (tmp_path / "artifacts" / "files" / "ab" / "abcdef" / "original.txt").is_file()

    def test_put_replaces_previous_content_and_leaves_no_temp_files(self, tmp_path: Path) -> None:
        store = LocalFileSystemArtifactStore(tmp_path)
        store.put(POINTER, b"first")

        store.put(POINTER, b"second")

        assert store.read(POINTER) == b"second"
        assert [path.name for path in (tmp_path / "files" / "ab" / "abcdef").iterdir()] == [
            "original.txt"
        ]

    def test_missing_artifact_reads_as_none(self, tmp_path: Path) -> None:
        store = LocalFileSystemArtifactStore(tmp_path)

        assert store.read(POINTER) is None
        assert not store.exists(POINTER)
        assert not store.delete(POINTER)

    def test_delete_removes_the_file_and_empty_parents_but_not_the_root(
        self, tmp_path: Path
    ) -> None:
        store = LocalFileSystemArtifactStore(tmp_path)
        store.put(POINTER, b"x")
        store.put(ArtifactPointer("files/zz/other.bin"), b"y")

        assert store.delete(POINTER)

        assert not (tmp_path / "files" / "ab").exists()
        assert (tmp_path / "files" / "zz" / "other.bin").is_file()
        assert tmp_path.is_dir()

    def test_symlink_escaping_the_root_is_refused(self, tmp_path: Path) -> None:
        root = tmp_path / "root"
        outside = tmp_path / "outside"
        outside.mkdir()
        store = LocalFileSystemArtifactStore(root)
        try:
            (root / "link").symlink_to(outside, target_is_directory=True)
        except OSError:
            pytest.skip("symlinks are not permitted on this file system")

        with pytest.raises(ValueError, match="escapes the store root"):
            store.put(ArtifactPointer("link/escaped.txt"), b"x")
