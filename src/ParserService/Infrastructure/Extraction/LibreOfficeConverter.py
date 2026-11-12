import os
import shutil
import subprocess
from pathlib import Path
from typing import ClassVar, Self

from ParserService.Domain.Documents.DetectedType import DetectedType
from ParserService.Domain.Errors.Result import Result
from ParserService.Domain.Jobs.FailureReason import FailureReason


class LibreOfficeConverter:
    """Converts legacy formats with headless LibreOffice, run as its own process (brief 2.6).

    Each conversion gets a private LibreOffice profile inside its temporary folder, so
    parallel conversions never share state. It inherits the worker's memory and CPU
    limits, and it is killed after ``TIMEOUT_SECONDS``. Its output is never logged.
    """

    EXECUTABLE: ClassVar[str] = "soffice"
    HOME_VARIABLE: ClassVar[str] = "HOME"
    TIMEOUT_SECONDS: ClassVar[float] = 120

    def __init__(self, executable: str) -> None:
        self._executable = executable

    @classmethod
    def available(cls) -> Self | None:
        """Find LibreOffice on this machine.

        Returns:
            A converter, or ``None`` when LibreOffice is not installed.
        """
        executable = shutil.which(cls.EXECUTABLE)
        return None if executable is None else cls(executable)

    def convert(
        self, source: Path, target: DetectedType, folder: Path
    ) -> Result[Path, FailureReason]:
        """Convert a file to another format.

        Args:
            source: The file to convert.
            target: The format to convert to, such as DOCX or XLSX.
            folder: A private folder for the output and the profile; created if missing.

        Returns:
            The converted file, or ``corrupted_file`` when LibreOffice cannot convert it.
        """
        folder.mkdir(parents=True, exist_ok=True)
        profile = (folder / "profile").as_uri()
        command = [self._executable, f"-env:UserInstallation={profile}", "--headless"]
        command += ["--norestore", "--convert-to", target.value, "--outdir", str(folder)]
        converted = folder / f"{source.stem}.{target.value}"
        if not self._run([*command, str(source)], folder) or not converted.exists():
            return Result.err(FailureReason.CORRUPTED_FILE)
        return Result.ok(converted)

    def _run(self, command: list[str], folder: Path) -> bool:
        # LibreOffice writes caches under HOME; the container is read-only, so use the folder.
        environment = {**os.environ, self.HOME_VARIABLE: str(folder)}
        try:
            completed = subprocess.run(  # noqa: S603 - fixed LibreOffice command
                command,
                capture_output=True,
                timeout=self.TIMEOUT_SECONDS,
                check=False,
                env=environment,
            )
        except subprocess.TimeoutExpired:
            return False
        return completed.returncode == 0
