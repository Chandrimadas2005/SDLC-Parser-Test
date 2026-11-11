from pathlib import Path
import shutil
import subprocess
import tempfile


class XlsCorpusGenerator:
    """Create legacy XLS fixtures from the synthetic XLSX corpus with LibreOffice."""

    def generate(self, root: Path) -> None:
        """Convert synthetic normal, hidden and empty workbooks to XLS."""
        self._convert(root / "xlsx" / "normal" / "normal.xlsx", root / "xls" / "normal")
        self._convert(root / "xlsx" / "hidden" / "hidden.xlsx", root / "xls" / "hidden")
        self._convert(root / "xlsx" / "empty" / "empty.xlsx", root / "xls" / "empty")
        self._copy_wrong_extension(root / "xls" / "normal" / "normal.xls", root / "xls" / "wrong-extension")
        (root / "xls" / "corrupted" / "corrupted.xls").write_bytes(b"not an xls workbook")

    def _convert(self, source: Path, destination: Path) -> None:
        destination.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as temporary:
            subprocess.run(
                ["libreoffice", "--headless", "--convert-to", "xls", "--outdir", temporary, str(source)],
                check=True,
                capture_output=True,
            )
            generated = Path(temporary) / f"{source.stem}.xls"
            shutil.copy2(generated, destination / generated.name)

    def _copy_wrong_extension(self, source: Path, destination: Path) -> None:
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination / "normal.txt")


if __name__ == "__main__":
    XlsCorpusGenerator().generate(Path(__file__).parents[1])
