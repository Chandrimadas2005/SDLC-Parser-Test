"""A FastAPI test client wired to in-memory fakes, plus handles on those fakes."""

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ParserService.Application.UseCases import (
    ArtifactKeys,
    DeleteParseJob,
    GetFailedParseJobs,
    GetParseBatch,
    GetParseJobResult,
    GetParseJobStatus,
    JobServices,
    RetryParseJob,
    SubmitParseBatch,
    SubmitParseJob,
    SubmitPolicy,
)
from ParserService.Domain.Jobs import Instant, ParserVersion
from ParserService.Infrastructure.Extraction import ExtractorRegistry
from ParserService.Infrastructure.Http import ApiDependencies, ParserApi, ReadinessCheck
from ParserService.Infrastructure.Logging import ServiceMetrics
from ParserService.Infrastructure.Persistence import DatabaseEngineFactory
from ParserService.Infrastructure.Storage import StoredBatchStore
from tests.Fakes import FixedClock, InMemoryArtifactStore, InMemoryJobQueue, InMemoryJobRepository

MAX_FILE_SIZE = 64
MAX_BATCH_FILES = 3
VERSION = ParserVersion("0.1.0-test")


@dataclass(frozen=True, slots=True)
class ApiHarness:
    client: TestClient
    repository: InMemoryJobRepository
    store: InMemoryArtifactStore
    queue: InMemoryJobQueue
    metrics: ServiceMetrics


def _readiness(tmp_path: Path) -> ReadinessCheck:
    engine = DatabaseEngineFactory().create(f"sqlite:///{(tmp_path / 'ready.sqlite3').as_posix()}")
    return ReadinessCheck(engine, tmp_path, min_free_bytes=1)


def _dependencies(services: JobServices, tmp_path: Path) -> ApiDependencies:
    repository, store = services.repository, services.store
    submit = SubmitParseJob(services, SubmitPolicy(VERSION, MAX_FILE_SIZE), ArtifactKeys())
    statuses, results = GetParseJobStatus(repository), GetParseJobResult(repository, store)
    batches = StoredBatchStore(store)
    return ApiDependencies(
        submit_parse_job=submit,
        get_parse_job_status=statuses,
        get_failed_parse_jobs=GetFailedParseJobs(repository),
        get_parse_job_result=results,
        retry_parse_job=RetryParseJob(services),
        delete_parse_job=DeleteParseJob(services, ArtifactKeys()),
        extractor_registry=ExtractorRegistry.default(),
        parser_version=VERSION.value,
        readiness=_readiness(tmp_path),
        metrics=ServiceMetrics(),
        submit_parse_batch=SubmitParseBatch(submit, batches, MAX_BATCH_FILES),
        get_parse_batch=GetParseBatch(batches, statuses, results),
    )


@pytest.fixture
def harness(tmp_path: Path) -> Iterator[ApiHarness]:
    repository, store, queue = InMemoryJobRepository(), InMemoryArtifactStore(), InMemoryJobQueue(5)
    services = JobServices(repository, store, queue, FixedClock(Instant(42_000)))
    dependencies = _dependencies(services, tmp_path)
    with TestClient(
        ParserApi(dependencies, VERSION.value).build(), raise_server_exceptions=False
    ) as client:
        yield ApiHarness(client, repository, store, queue, dependencies.metrics)
