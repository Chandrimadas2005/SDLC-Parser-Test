import os
import shutil
from collections.abc import Iterator
from pathlib import Path


class LocalTemporaryFileCleaner:
    """Remove abandoned artifact writes and temporary directories of dead workers."""

    def __init__(self, root: Path, worker_temp_root: Path) -> None:
        self._root = root.resolve()
        self._worker_temp_root = worker_temp_root.resolve()

    def clean(self) -> None:
        """Remove incomplete files and temporary directories owned by dead workers."""
        self._remove_files()
        if self._worker_temp_root.exists():
            self._remove_directories()

    def _remove_files(self) -> None:
        for temporary in self._abandoned(self._root.rglob(".tmp-*")):
            if temporary.is_file():
                temporary.unlink()

    def _remove_directories(self) -> None:
        for directory in self._abandoned(self._worker_temp_root.glob("parse-*")):
            if directory.is_dir():
                shutil.rmtree(directory)

    def _abandoned(self, paths: Iterator[Path]) -> Iterator[Path]:
        return (path for path in paths if not self._process_is_alive(path.name))

    @staticmethod
    def _process_is_alive(directory_name: str) -> bool:
        try:
            process_id = int(directory_name.split("-")[1])
            os.kill(process_id, 0)
        except (ValueError, ProcessLookupError):
            return False
        except PermissionError:
            return True
        return True
