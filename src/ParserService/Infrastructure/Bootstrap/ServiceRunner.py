import os
from typing import Final

import structlog
import uvicorn
from fastapi import FastAPI

from ParserService.Infrastructure.Bootstrap.ServiceContainer import ServiceContainer
from ParserService.Infrastructure.Config.Settings import Settings
from ParserService.Infrastructure.Logging.LoggingConfigurator import LoggingConfigurator


class ServiceRunner:
    """Process entry point: read settings, configure logging, migrate, serve.

    ``parser-api`` (see ``pyproject.toml``) calls ``main``. Uvicorn is given
    ``create_app`` as an application factory.
    """

    FACTORY: Final = "ParserService.Infrastructure.Bootstrap.ServiceRunner:ServiceRunner.create_app"

    @classmethod
    def create_app(cls) -> FastAPI:
        """Build the application from the environment, applying migrations first.

        Returns:
            The FastAPI app.
        """
        settings = Settings.from_environment(os.environ)
        LoggingConfigurator().configure(settings.log_level)
        container = ServiceContainer(settings)
        container.migrate()
        structlog.get_logger(__name__).info(
            "service_started", parser_version=container.parser_version.value
        )
        return container.api()

    @classmethod
    def main(cls) -> None:
        """Serve the application with Uvicorn until the process is stopped."""
        settings = Settings.from_environment(os.environ)
        uvicorn.run(
            cls.FACTORY,
            factory=True,
            host=settings.http_host,
            port=settings.http_port,
            log_level=settings.log_level.lower(),
            access_log=False,
        )
