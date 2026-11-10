import shutil
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError

from ParserService.Infrastructure.Http.ReadinessComponent import ReadinessComponent


class ReadinessCheck:
    """Decides whether the service may accept work: database reachable, disk not nearly full."""

    def __init__(self, engine: Engine, artifact_root: Path, min_free_bytes: int) -> None:
        self._engine = engine
        self._artifact_root = artifact_root
        self._min_free_bytes = min_free_bytes

    def failing(self) -> list[ReadinessComponent]:
        """Run every probe.

        Returns:
            The components that are not healthy; empty when the service is ready.
        """
        failing = []
        if not self._database_reachable():
            failing.append(ReadinessComponent.DATABASE)
        if not self._disk_has_room():
            failing.append(ReadinessComponent.DISK)
        return failing

    def _database_reachable(self) -> bool:
        try:
            with self._engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except OperationalError:
            return False
        return True

    def _disk_has_room(self) -> bool:
        probe = self._artifact_root if self._artifact_root.exists() else Path.cwd()
        return shutil.disk_usage(probe).free >= self._min_free_bytes
