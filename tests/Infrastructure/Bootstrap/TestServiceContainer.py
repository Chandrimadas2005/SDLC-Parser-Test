from http import HTTPStatus
from pathlib import Path

from fastapi.testclient import TestClient

from ParserService.Domain.Jobs import JobId, JobStatus
from ParserService.Infrastructure.Bootstrap import ServiceContainer
from ParserService.Infrastructure.Config import EnvironmentVariable, Settings


class TestServiceContainer:
    """The wired service accepts a text file over HTTP and stores it durably."""

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

    def test_text_file_goes_in_and_a_queued_job_comes_out(self, tmp_path: Path) -> None:
        container = self._container(tmp_path)

        with TestClient(container.api()) as client:
            submitted = client.post(
                "/v1/parse-jobs", files={"file": ("hello.txt", b"Hello, parser!", "text/plain")}
            )
            status = client.get(f"/v1/parse-jobs/{submitted.json()['job_id']}")
            ready = client.get("/health/ready")

        assert submitted.status_code == HTTPStatus.ACCEPTED
        assert status.json()["status"] == JobStatus.QUEUED
        assert status.json()["parser_version"] == container.parser_version.value
        assert ready.status_code == HTTPStatus.OK
        job = container.repository.get(JobId(submitted.json()["job_id"]))
        assert job is not None
        assert container.store.read(job.file_pointer) == b"Hello, parser!"
        assert container.queue.claim() == job.id

    def test_migrate_is_idempotent(self, tmp_path: Path) -> None:
        container = self._container(tmp_path)

        container.migrate()

        assert container.queue.depth() == 0
