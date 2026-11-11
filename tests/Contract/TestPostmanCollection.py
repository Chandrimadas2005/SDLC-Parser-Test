import json
from http import HTTPStatus
from pathlib import Path
from typing import Final

from fastapi.testclient import TestClient

from ParserService.Infrastructure.Bootstrap import ServiceContainer
from ParserService.Infrastructure.Config import EnvironmentVariable, Settings
from tests.Contract.PostmanKey import PostmanKey

ROOT: Final = Path(__file__).resolve().parents[2]
COLLECTION: Final = ROOT / "docs" / "postman" / "parser-service.postman_collection.json"
BASE_URL: Final = "{{baseUrl}}"
JOB_ID: Final = "{{jobId}}"


class TestPostmanCollection:
    """The shared Postman collection only calls endpoints that exist, with their real codes."""

    @staticmethod
    def _requests() -> list[tuple[str, str]]:
        collection = json.loads(COLLECTION.read_text(encoding="utf-8"))
        found: list[tuple[str, str]] = []
        for folder in collection[PostmanKey.ITEM]:
            for item in folder[PostmanKey.ITEM]:
                request = item[PostmanKey.REQUEST]
                found.append((request[PostmanKey.METHOD], request[PostmanKey.URL][PostmanKey.RAW]))
        return found

    @staticmethod
    def _client(tmp_path: Path) -> TestClient:
        database = (tmp_path / "db.sqlite3").as_posix()
        settings = Settings.from_environment(
            {
                EnvironmentVariable.DATABASE_URL: f"sqlite:///{database}",
                EnvironmentVariable.ARTIFACT_ROOT: str(tmp_path / "artifacts"),
            }
        )
        container = ServiceContainer(settings)
        container.migrate()
        return TestClient(container.api())

    def test_every_request_uses_the_base_url_variable(self) -> None:
        collection = json.loads(COLLECTION.read_text(encoding="utf-8"))
        variables = {entry[PostmanKey.KEY] for entry in collection[PostmanKey.VARIABLE]}

        assert variables == {"baseUrl", "jobId"}
        assert all(url.startswith(BASE_URL) for _, url in self._requests())

    def test_every_request_answers_as_the_collection_expects(self, tmp_path: Path) -> None:
        with self._client(tmp_path) as client:
            submitted = client.post("/v1/parse-jobs", files={"file": ("a.txt", b"Synthetic.\n")})
            job_id = submitted.json()["job_id"]
            codes = {
                (method, url): client.request(
                    method, url.removeprefix(BASE_URL).replace(JOB_ID, job_id)
                ).status_code
                for method, url in self._requests()
                if method == "GET"
            }

        assert submitted.status_code == HTTPStatus.ACCEPTED
        unknown = [code for (_, url), code in codes.items() if url.endswith("0000")]
        known = [code for (_, url), code in codes.items() if not url.endswith("0000")]
        assert unknown == [HTTPStatus.NOT_FOUND]
        assert set(known) == {HTTPStatus.OK}
