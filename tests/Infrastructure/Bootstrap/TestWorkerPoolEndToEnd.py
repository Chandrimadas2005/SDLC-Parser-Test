import threading
from http import HTTPStatus
from pathlib import Path

from fastapi.testclient import TestClient

from ParserService.Infrastructure.Bootstrap import ServiceContainer, WorkerLoop, WorkerPool
from ParserService.Infrastructure.Config import EnvironmentVariable, Settings


class TestWorkerPoolEndToEnd:
    """Real files through the API and a pool of three slots: every job succeeds once."""

    @staticmethod
    def _container(tmp_path: Path) -> ServiceContainer:
        database = (tmp_path / "db.sqlite3").as_posix()
        settings = Settings.from_environment(
            {
                EnvironmentVariable.DATABASE_URL: f"sqlite:///{database}",
                EnvironmentVariable.ARTIFACT_ROOT: str(tmp_path / "artifacts"),
            }
        )
        container = ServiceContainer(settings)
        container.migrate()
        return container

    def test_pool_parses_several_files_at_once(self, tmp_path: Path) -> None:
        container = self._container(tmp_path)
        with TestClient(container.api()) as client:
            for n in range(6):
                content = f"Synthetic note {n}.\n".encode()
                files = {"file": (f"note-{n}.txt", content, "text/plain")}
                assert client.post("/v1/parse-jobs", files=files).status_code == HTTPStatus.ACCEPTED

        stop = threading.Event()
        loops = [WorkerLoop(container.process_next_job(), stop) for _ in range(3)]
        processed = self._run(loops, stop)

        assert processed == 6
        assert container.queue.depth() == 0

    @staticmethod
    def _run(loops: list[WorkerLoop], stop: threading.Event) -> int:
        timer = threading.Timer(6.0, stop.set)
        timer.start()
        total = WorkerPool(loops).run()
        timer.cancel()
        return total

    def test_files_uploaded_together_come_back_as_one_combined_result(self, tmp_path: Path) -> None:
        container = self._container(tmp_path)
        with TestClient(container.api()) as client:
            files = [
                ("file", (f"part-{n}.md", f"# Part {n}\n".encode(), "text/markdown"))
                for n in range(3)
            ]
            batch = client.post("/v1/parse-jobs", files=files).json()["batch_id"]
            stop = threading.Event()
            self._run([WorkerLoop(container.process_next_job(), stop) for _ in range(3)], stop)
            combined = client.get(f"/v1/parse-batches/{batch}/result").json()

        headings = [file["result"]["elements"][0]["text"] for file in combined["files"]]
        assert combined["status"] == "succeeded"
        assert headings == ["Part 0", "Part 1", "Part 2"]
