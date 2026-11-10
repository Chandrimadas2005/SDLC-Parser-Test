from dataclasses import dataclass

from ParserService.Application.UseCases.GetParseJobStatus import GetParseJobStatus
from ParserService.Application.UseCases.SubmitParseJob import SubmitParseJob
from ParserService.Infrastructure.Http.ReadinessCheck import ReadinessCheck
from ParserService.Infrastructure.Logging.ServiceMetrics import ServiceMetrics


@dataclass(frozen=True, slots=True)
class ApiDependencies:
    """Everything the HTTP layer needs, assembled by the composition root."""

    submit_parse_job: SubmitParseJob
    get_parse_job_status: GetParseJobStatus
    readiness: ReadinessCheck
    metrics: ServiceMetrics
