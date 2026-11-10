import json
import threading
from http import HTTPStatus
from pathlib import Path

from fastapi.testclient import TestClient

from ParserService.Domain.Jobs import JobId, JobStatus
from ParserService.Infrastructure.Bootstrap import ServiceContainer, WorkerLoop
from ParserService.Infrastructure.Config import EnvironmentVariable, Settings
from ParserService.Infrastructure.Output import OutputField


class TestWorkerLoop:
    """Phase 0 end to end: a text file goes in and comes out as a ParsedDocument."""

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

    @staticmethod
    def _submit(container: ServiceContainer) -> JobId:
        content = b"Hello, parser!\n\nSecond paragraph.\n"
        with TestClient(container.api()) as client:
            submitted = client.post(
                "/v1/parse-jobs", files={"file": ("hello.txt", content, "text/plain")}
            )
        assert submitted.status_code == HTTPStatus.ACCEPTED
        return JobId(submitted.json()["job_id"])

    def test_submitted_text_file_is_parsed_into_a_parsed_document(self, tmp_path: Path) -> None:
        container = self._container(tmp_path)
        job_id = self._submit(container)

        processed = WorkerLoop(container.process_next_job(), threading.Event()).drain()

        job = container.repository.get(job_id)
        assert processed == 1
        assert job is not None
        assert job.status is JobStatus.SUCCEEDED
        assert job.result_pointer is not None
        stored = container.store.read(job.result_pointer)
        assert stored is not None
        result = json.loads(stored)
        assert result[OutputField.STATUS] == "succeeded"
        assert len(result[OutputField.ELEMENTS]) == 2

    def test_run_processes_jobs_until_stopped(self, tmp_path: Path) -> None:
        container = self._container(tmp_path)
        self._submit(container)
        stop = threading.Event()
        loop = WorkerLoop(container.process_next_job(), stop)
        timer = threading.Timer(1.5, stop.set)
        timer.start()

        processed = loop.run()

        timer.cancel()
        assert processed == 1
