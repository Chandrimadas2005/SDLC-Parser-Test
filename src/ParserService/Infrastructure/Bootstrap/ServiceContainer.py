from importlib.metadata import PackageNotFoundError, version
from typing import Final

from fastapi import FastAPI

from ParserService.Application.UseCases.ArtifactKeys import ArtifactKeys
from ParserService.Application.UseCases.DeleteParseJob import DeleteParseJob
from ParserService.Application.UseCases.GetParseJobResult import GetParseJobResult
from ParserService.Application.UseCases.GetParseJobStatus import GetParseJobStatus
from ParserService.Application.UseCases.RetryParseJob import RetryParseJob
from ParserService.Application.UseCases.JobServices import JobServices
from ParserService.Application.UseCases.ProcessNextJob import ProcessNextJob
from ParserService.Application.UseCases.SubmitParseJob import SubmitParseJob
from ParserService.Application.UseCases.SubmitPolicy import SubmitPolicy
from ParserService.Domain.Jobs.ParserVersion import ParserVersion
from ParserService.Infrastructure.Config.Settings import Settings
from ParserService.Infrastructure.Extraction.ExtractorRegistry import ExtractorRegistry
from ParserService.Infrastructure.Http.ApiDependencies import ApiDependencies
from ParserService.Infrastructure.Http.ParserApi import ParserApi
from ParserService.Infrastructure.Http.ReadinessCheck import ReadinessCheck
from ParserService.Infrastructure.Isolation.IsolatedDocumentParser import IsolatedDocumentParser
from ParserService.Infrastructure.Isolation.IsolatedParseRunner import IsolatedParseRunner
from ParserService.Infrastructure.Isolation.WorkerLimits import WorkerLimits
from ParserService.Infrastructure.Logging.ServiceMetrics import ServiceMetrics
from ParserService.Infrastructure.Persistence.DatabaseEngineFactory import DatabaseEngineFactory
from ParserService.Infrastructure.Persistence.JobRecordMapper import JobRecordMapper
from ParserService.Infrastructure.Persistence.MigrationRunner import MigrationRunner
from ParserService.Infrastructure.Persistence.PostgresJobRepository import PostgresJobRepository
from ParserService.Infrastructure.Queue.PostgresJobQueue import PostgresJobQueue
from ParserService.Infrastructure.Storage.LocalFileSystemArtifactStore import (
    LocalFileSystemArtifactStore,
)
from ParserService.Infrastructure.Time.SystemClock import SystemClock


class ServiceContainer:
    """Composition root: wires adapters to ports and ports to use cases, from Settings.

    This is the only place that knows every concrete class. Everything else receives
    its collaborators through constructors.
    """

    DISTRIBUTION: Final = "parser-service"
    FALLBACK_VERSION: Final = "0.0.0-dev"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.engine = DatabaseEngineFactory().create(settings.database_url)
        self.clock = SystemClock()
        self.metrics = ServiceMetrics()
        self.repository = PostgresJobRepository(self.engine, JobRecordMapper())
        self.store = LocalFileSystemArtifactStore(settings.artifact_root)
        self.queue = PostgresJobQueue(self.engine, self.clock, settings.limits.queue_capacity)
        self.parser_version = self._parser_version()

    def migrate(self) -> None:
        """Bring the Parser's schema to the latest revision."""
        MigrationRunner(self.engine).upgrade()

    def api(self) -> FastAPI:
        """Build the HTTP application.

        Returns:
            The FastAPI app with every route wired to its use case.
        """
        services = JobServices(self.repository, self.store, self.queue, self.clock)
        policy = SubmitPolicy(self.parser_version, self.settings.limits.max_file_size_bytes)
        keys = ArtifactKeys()
        dependencies = ApiDependencies(
            submit_parse_job=SubmitParseJob(services, policy, keys),
            get_parse_job_status=GetParseJobStatus(self.repository),
            get_parse_job_result=GetParseJobResult(self.repository, self.store),
            retry_parse_job=RetryParseJob(services),
            delete_parse_job=DeleteParseJob(services, keys),
            extractor_registry=ExtractorRegistry.default(),
            parser_version=self.parser_version.value,
            readiness=ReadinessCheck(
                self.engine, self.settings.artifact_root, self.settings.limits.min_free_disk_bytes
            ),
            metrics=self.metrics,
        )
        return ParserApi(dependencies, self.parser_version.value).build()

    def process_next_job(self) -> ProcessNextJob:
        """Build the worker's use case: parse each queued file in an isolated process.

        Returns:
            The use case, wired to the isolated parser and the job ports.
        """
        services = JobServices(self.repository, self.store, self.queue, self.clock)
        limits = self.settings.limits
        runner = IsolatedParseRunner(
            WorkerLimits(limits.job_timeout_seconds, limits.job_memory_limit_mb)
        )
        parser = IsolatedDocumentParser(self.settings.artifact_root, runner)
        return ProcessNextJob(services, parser, ArtifactKeys())

    @classmethod
    def _parser_version(cls) -> ParserVersion:
        try:
            return ParserVersion(version(cls.DISTRIBUTION))
        except PackageNotFoundError:
            return ParserVersion(cls.FALLBACK_VERSION)
