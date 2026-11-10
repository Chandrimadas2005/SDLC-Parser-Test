from http import HTTPStatus
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from ParserService.Infrastructure.Http import (
    ErrorEnvelopeHandler,
    HealthRouter,
    HttpStatusMapping,
    ReadinessCheck,
    ReadinessComponent,
)
from ParserService.Infrastructure.Persistence import DatabaseEngineFactory
from tests.Infrastructure.Http.conftest import ApiHarness


class TestHealthApi:
    """Live answers whenever the process runs; ready reflects database and disk probes."""

    def test_live_is_always_ok(self, harness: ApiHarness) -> None:
        response = harness.client.get("/health/live")

        assert response.status_code == HTTPStatus.OK
        assert response.json() == {"status": "live"}

    def test_ready_when_database_and_disk_are_fine(self, harness: ApiHarness) -> None:
        response = harness.client.get("/health/ready")

        assert response.status_code == HTTPStatus.OK
        assert response.json() == {"status": "ready"}

    def test_not_ready_uses_the_envelope(self, tmp_path: Path) -> None:
        engine = DatabaseEngineFactory().create(f"sqlite:///{tmp_path.as_posix()}")
        readiness = ReadinessCheck(engine, tmp_path, min_free_bytes=1)
        app = FastAPI()
        app.include_router(HealthRouter(readiness).router)
        ErrorEnvelopeHandler(HttpStatusMapping()).install(app)

        response = TestClient(app).get("/health/ready")

        assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
        assert response.json()["code"] == "not_ready"

    def test_probes_report_which_component_fails(self, tmp_path: Path) -> None:
        good_engine = DatabaseEngineFactory().create(f"sqlite:///{(tmp_path / 'ok.db').as_posix()}")
        bad_engine = DatabaseEngineFactory().create(f"sqlite:///{tmp_path.as_posix()}")
        huge = 1 << 62

        assert ReadinessCheck(good_engine, tmp_path, 1).failing() == []
        assert ReadinessCheck(bad_engine, tmp_path, 1).failing() == [ReadinessComponent.DATABASE]
        assert ReadinessCheck(good_engine, tmp_path, huge).failing() == [ReadinessComponent.DISK]
        assert ReadinessCheck(good_engine, tmp_path / "missing", huge).failing() == [
            ReadinessComponent.DISK
        ]
