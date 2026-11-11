"""A FastAPI test client wired to in-memory fakes, plus handles on those fakes."""

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ParserService.Application.UseCases import (
    ArtifactKeys,
    DeleteParseJob,
    GetParseJobResult,
    GetParseJobStatus,
    RetryParseJob,
    JobServices,
    SubmitParseJob,
    SubmitPolicy,
)
from ParserService.Domain.Jobs import Instant, ParserVersion
from ParserService.Infrastructure.Extraction import ExtractorRegistry
from ParserService.Infrastructure.Http import ApiDependencies, ParserApi, ReadinessCheck
from ParserService.Infrastructure.Logging import ServiceMetrics
from ParserService.Infrastructure.Persistence import DatabaseEngineFactory
from tests.Fakes import FixedClock, InMemoryArtifactStore, InMemoryJobQueue, InMemoryJobRepository

MAX_FILE_SIZE = 64
VERSION = ParserVersion("0.1.0-test")


@dataclass(frozen=True, slots=True)
class ApiHarness:
    client: TestClient
    repository: InMemoryJobRepository
    store: InMemoryArtifactStore
    queue: InMemoryJobQueue
    metrics: ServiceMetrics


@pytest.fixture
def harness(tmp_path: Path) -> Iterator[ApiHarness]:
    repository, store, queue = InMemoryJobRepository(), InMemoryArtifactStore(), InMemoryJobQueue(5)
    services = JobServices(repository, store, queue, FixedClock(Instant(42_000)))
    engine = DatabaseEngineFactory().create(f"sqlite:///{(tmp_path / 'ready.sqlite3').as_posix()}")
    dependencies = ApiDependencies(
        submit_parse_job=SubmitParseJob(
            services, SubmitPolicy(VERSION, MAX_FILE_SIZE), ArtifactKeys()
        ),
        get_parse_job_status=GetParseJobStatus(repository),
        get_parse_job_result=GetParseJobResult(repository, store),
        retry_parse_job=RetryParseJob(services),
        delete_parse_job=DeleteParseJob(services, ArtifactKeys()),
        extractor_registry=ExtractorRegistry.default(),
        parser_version=VERSION.value,
        readiness=ReadinessCheck(engine, tmp_path, min_free_bytes=1),
        metrics=ServiceMetrics(),
    )
    with TestClient(ParserApi(dependencies, VERSION.value).build(), raise_server_exceptions=False) as client:
        yield ApiHarness(client, repository, store, queue, dependencies.metrics)
