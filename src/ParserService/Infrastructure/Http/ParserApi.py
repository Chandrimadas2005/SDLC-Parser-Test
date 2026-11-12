from typing import Final

from fastapi import FastAPI

from ParserService.Infrastructure.Http.ApiDependencies import ApiDependencies
from ParserService.Infrastructure.Http.ErrorEnvelopeHandler import ErrorEnvelopeHandler
from ParserService.Infrastructure.Http.FormatsRouter import FormatsRouter
from ParserService.Infrastructure.Http.HealthRouter import HealthRouter
from ParserService.Infrastructure.Http.HttpStatusMapping import HttpStatusMapping
from ParserService.Infrastructure.Http.MetricsRouter import MetricsRouter
from ParserService.Infrastructure.Http.ParseJobsRouter import ParseJobsRouter
from ParserService.Infrastructure.Http.RequestIdMiddleware import RequestIdMiddleware


class ParserApi:
    """Assembles the FastAPI application: routers, middleware and error handling."""

    TITLE: Final = "Parser Service"

    def __init__(self, dependencies: ApiDependencies, version: str) -> None:
        self._dependencies = dependencies
        self._version = version

    def build(self) -> FastAPI:
        """Create the application.

        Returns:
            A FastAPI app ready to be served by Uvicorn or a test client.
        """
        app = FastAPI(title=self.TITLE, version=self._version)
        app.add_middleware(RequestIdMiddleware)
        ErrorEnvelopeHandler(HttpStatusMapping()).install(app)
        jobs = ParseJobsRouter(self._dependencies)
        app.include_router(jobs.router)
        formats = FormatsRouter(
            self._dependencies.extractor_registry, self._dependencies.parser_version
        )
        app.include_router(formats.router)
        app.include_router(HealthRouter(self._dependencies.readiness).router)
        app.include_router(MetricsRouter(self._dependencies.metrics).router)
        return app
