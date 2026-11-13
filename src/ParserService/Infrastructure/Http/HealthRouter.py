from http import HTTPStatus
from typing import Final

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ParserService.Application.Errors.ApplicationErrorCode import ApplicationErrorCode
from ParserService.Infrastructure.Http.ApiError import ApiError
from ParserService.Infrastructure.Http.HealthField import HealthField
from ParserService.Infrastructure.Http.ReadinessCheck import ReadinessCheck


class HealthRouter:
    """``/health/live`` (process is up) and ``/health/ready`` (may accept work)."""

    PREFIX: Final = "/health"
    LIVE: Final = "live"
    READY: Final = "ready"

    def __init__(self, readiness: ReadinessCheck) -> None:
        self._readiness = readiness
        self.router = APIRouter(prefix=self.PREFIX)
        self.router.add_api_route(
            "/live",
            self.live,
            methods=["GET"],
            summary="Liveness check",
            description="Returns 200 when the API process is serving requests.",
        )
        self.router.add_api_route(
            "/ready",
            self.ready,
            methods=["GET"],
            summary="Readiness check",
            description="Returns 200 when dependencies and disk are ready, otherwise 503.",
        )

    async def live(self) -> JSONResponse:
        """Answer as soon as the process serves requests.

        Returns:
            ``200`` with ``{"status": "live"}``.
        """
        return JSONResponse({HealthField.STATUS: self.LIVE}, status_code=HTTPStatus.OK)

    async def ready(self) -> JSONResponse:
        """Answer ``200`` when every readiness probe passes, else ``503``.

        Returns:
            ``200`` with the ready status.

        Raises:
            ApiError: ``NOT_READY`` when a probe fails; the envelope is returned.
        """
        failing = self._readiness.failing()
        if failing:
            raise ApiError(ApplicationErrorCode.NOT_READY)
        return JSONResponse({HealthField.STATUS: self.READY}, status_code=HTTPStatus.OK)
