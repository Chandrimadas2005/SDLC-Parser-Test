from dataclasses import dataclass

from ParserService.Application.UseCases.DeleteParseJob import DeleteParseJob
from ParserService.Application.UseCases.GetParseJobResult import GetParseJobResult
from ParserService.Application.UseCases.GetParseJobStatus import GetParseJobStatus
from ParserService.Application.UseCases.RetryParseJob import RetryParseJob
from ParserService.Application.UseCases.SubmitParseJob import SubmitParseJob
from ParserService.Infrastructure.Extraction.ExtractorRegistry import ExtractorRegistry
from ParserService.Infrastructure.Http.ReadinessCheck import ReadinessCheck
from ParserService.Infrastructure.Logging.ServiceMetrics import ServiceMetrics


@dataclass(frozen=True, slots=True)
class ApiDependencies:
    """Everything the HTTP layer needs, assembled by the composition root."""

    submit_parse_job: SubmitParseJob
    get_parse_job_status: GetParseJobStatus
    get_parse_job_result: GetParseJobResult
    retry_parse_job: RetryParseJob
    delete_parse_job: DeleteParseJob
    extractor_registry: ExtractorRegistry
    parser_version: str
    readiness: ReadinessCheck
    metrics: ServiceMetrics
