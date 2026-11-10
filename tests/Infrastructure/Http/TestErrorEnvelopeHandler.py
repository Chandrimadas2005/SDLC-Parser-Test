from http import HTTPStatus

from fastapi import FastAPI
from fastapi.testclient import TestClient

from ParserService.Infrastructure.Http import (
    ErrorEnvelopeHandler,
    HttpStatusMapping,
    RequestIdMiddleware,
)


class _Boom:
    async def explode(self) -> None:
        message = "secret-document-content"
        raise RuntimeError(message)


class TestErrorEnvelopeHandler:
    """Unexpected exceptions become a 500 envelope with the request ID, never a stack trace."""

    def test_unexpected_exception_is_500_envelope(self) -> None:
        app = FastAPI()
        app.add_middleware(RequestIdMiddleware)
        app.add_api_route("/boom", _Boom().explode, methods=["GET"])
        ErrorEnvelopeHandler(HttpStatusMapping()).install(app)

        response = TestClient(app, raise_server_exceptions=False).get("/boom")

        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
        body = response.json()
        assert body["code"] == "internal_error"
        assert body["request_id"] == response.headers["X-Request-ID"]
        assert "secret-document-content" not in response.text

    def test_request_id_header_is_generated_when_absent_and_echoed_when_present(self) -> None:
        app = FastAPI()
        app.add_middleware(RequestIdMiddleware)

        generated = TestClient(app).get("/missing")
        echoed = TestClient(app).get("/missing", headers={"X-Request-ID": "abc-123"})

        assert len(generated.headers["X-Request-ID"]) == 36
        assert echoed.headers["X-Request-ID"] == "abc-123"
