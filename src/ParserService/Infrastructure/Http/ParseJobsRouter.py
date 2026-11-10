from http import HTTPStatus
from typing import Annotated, Final

import structlog
from fastapi import APIRouter, File, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

from ParserService.Application.Dto.ParseJobSubmitted import ParseJobSubmitted
from ParserService.Application.Dto.SubmitParseJobCommand import SubmitParseJobCommand
from ParserService.Application.Errors.ApplicationErrorCode import ApplicationErrorCode
from ParserService.Application.UseCases.GetParseJobStatus import GetParseJobStatus
from ParserService.Application.UseCases.SubmitParseJob import SubmitParseJob
from ParserService.Domain.Jobs.FileName import FileName
from ParserService.Domain.Jobs.JobId import JobId
from ParserService.Infrastructure.Http.ApiError import ApiError
from ParserService.Infrastructure.Http.HttpHeader import HttpHeader
from ParserService.Infrastructure.Http.ParseJobStatusResponse import ParseJobStatusResponse
from ParserService.Infrastructure.Http.ParseJobSubmittedResponse import ParseJobSubmittedResponse
from ParserService.Infrastructure.Logging.LogField import LogField
from ParserService.Infrastructure.Logging.ServiceMetrics import ServiceMetrics


class ParseJobsRouter:
    """``POST /v1/parse-jobs`` and ``GET /v1/parse-jobs/{id}`` (brief, section 2.4)."""

    PREFIX: Final = "/v1/parse-jobs"
    RETRY_AFTER_SECONDS: Final = 30
    DEFAULT_FILE_NAME: Final = "upload"
    OUTCOME_CREATED: Final = "created"
    OUTCOME_EXISTING: Final = "existing"

    def __init__(
        self, submit: SubmitParseJob, status: GetParseJobStatus, metrics: ServiceMetrics
    ) -> None:
        self._submit = submit
        self._status = status
        self._metrics = metrics
        self._log = structlog.get_logger(__name__)
        self.router = APIRouter(prefix=self.PREFIX)
        self.router.add_api_route(
            "",
            self.submit_job,
            methods=["POST"],
            status_code=HTTPStatus.ACCEPTED,
            response_model=ParseJobSubmittedResponse,
        )
        self.router.add_api_route(
            "/{job_id}",
            self.job_status,
            methods=["GET"],
            response_model=ParseJobStatusResponse,
        )

    async def submit_job(
        self, request: Request, file: Annotated[UploadFile, File()]
    ) -> JSONResponse:
        """Accept a file and answer ``202`` with the job to poll.

        Args:
            request: The incoming request, used to build the ``Location`` header.
            file: The uploaded file (multipart field ``file``).

        Returns:
            The submission response.

        Raises:
            ApiError: ``FILE_TOO_LARGE``, ``QUEUE_FULL``, ``STORAGE_UNAVAILABLE`` or
                ``INVALID_REQUEST``.
        """
        command = SubmitParseJobCommand(self._file_name(file), await file.read())
        result = await run_in_threadpool(self._submit.execute, command)
        if result.is_err:
            self._metrics.record_submission(result.unwrap_err().value)
            raise self._submission_error(result.unwrap_err())
        submitted = result.unwrap()
        self._record(submitted, len(command.content))
        location = str(request.url_for(self.job_status.__name__, job_id=submitted.job_id.value))
        body = ParseJobSubmittedResponse.of(submitted).model_dump(mode="json")
        headers = {HttpHeader.LOCATION.value: location}
        return JSONResponse(body, status_code=HTTPStatus.ACCEPTED, headers=headers)

    def _record(self, submitted: ParseJobSubmitted, size_bytes: int) -> None:
        outcome = self.OUTCOME_EXISTING if submitted.already_existed else self.OUTCOME_CREATED
        self._metrics.record_submission(outcome)
        self._log.info(
            "job_submitted",
            **{
                LogField.JOB_ID: submitted.job_id.value,
                LogField.SIZE_BYTES: size_bytes,
                LogField.STATUS: outcome,
            },
        )

    async def job_status(self, job_id: str) -> ParseJobStatusResponse:
        """Report the status and failure reason of a job.

        Args:
            job_id: The job identifier from the path.

        Returns:
            The status response.

        Raises:
            ApiError: ``INVALID_REQUEST`` for a malformed ID, ``JOB_NOT_FOUND`` otherwise.
        """
        result = await run_in_threadpool(self._status.execute, self._job_id(job_id))
        if result.is_err:
            raise ApiError(result.unwrap_err())
        return ParseJobStatusResponse.of(result.unwrap())

    def _file_name(self, file: UploadFile) -> FileName:
        try:
            return FileName(file.filename or self.DEFAULT_FILE_NAME)
        except ValueError as error:
            raise ApiError(ApplicationErrorCode.INVALID_REQUEST) from error

    @staticmethod
    def _job_id(raw: str) -> JobId:
        try:
            return JobId(raw)
        except ValueError as error:
            raise ApiError(ApplicationErrorCode.INVALID_REQUEST) from error

    def _submission_error(self, code: ApplicationErrorCode) -> ApiError:
        if code is ApplicationErrorCode.QUEUE_FULL:
            return ApiError(code, retry_after_seconds=self.RETRY_AFTER_SECONDS)
        return ApiError(code)
