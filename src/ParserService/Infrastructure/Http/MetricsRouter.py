from typing import Final

from fastapi import APIRouter
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST

from ParserService.Infrastructure.Logging.ServiceMetrics import ServiceMetrics


class MetricsRouter:
    """``/metrics`` in the Prometheus text format."""

    PATH: Final = "/metrics"

    def __init__(self, metrics: ServiceMetrics) -> None:
        self._metrics = metrics
        self.router = APIRouter()
        self.router.add_api_route(
            self.PATH,
            self.metrics,
            methods=["GET"],
            summary="Prometheus metrics",
            description="Returns service counters in Prometheus exposition format.",
        )

    async def metrics(self) -> Response:
        """Render the registry.

        Returns:
            The scrape body with the Prometheus content type.
        """
        return Response(self._metrics.render(), media_type=CONTENT_TYPE_LATEST)
