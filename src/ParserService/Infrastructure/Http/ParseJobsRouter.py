from http import HTTPStatus
from typing import Annotated, Final

import structlog
from fastapi import APIRouter, File, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, Response

from ParserService.Application.Dto.ParseJobSubmitted import ParseJobSubmitted
from ParserService.Application.Dto.SubmitParseJobCommand import SubmitParseJobCommand
from ParserService.Application.Errors.ApplicationErrorCode import ApplicationErrorCode
from ParserService.Domain.Jobs.FileName import FileName
from ParserService.Domain.Jobs.JobId import JobId
from ParserService.Infrastructure.Http.ApiDependencies import ApiDependencies
from ParserService.Infrastructure.Http.ApiError import ApiError
from ParserService.Infrastructure.Http.HttpHeader import HttpHeader
from ParserService.Infrastructure.Http.ParseJobStatusResponse import ParseJobStatusResponse
from ParserService.Infrastructure.Http.ParseJobSubmittedResponse import ParseJobSubmittedResponse
from ParserService.Infrastructure.Logging.LogField import LogField
from ParserService.Infrastructure.Output.ParsedDocumentMarkdownRenderer import (
    ParsedDocumentMarkdownRenderer,
)


class ParseJobsRouter:
    """Submit, inspect, retrieve, retry and delete parse jobs through the HTTP API."""

    PREFIX: Final = "/v1/parse-jobs"
    RETRY_AFTER_SECONDS: Final = 30
    DEFAULT_FILE_NAME: Final = "upload"
    OUTCOME_CREATED: Final = "created"
    OUTCOME_EXISTING: Final = "existing"

    def __init__(self, dependencies: ApiDependencies) -> None:
        self._dependencies = dependencies
        self._submit = dependencies.submit_parse_job
        self._status = dependencies.get_parse_job_status
        self._metrics = dependencies.metrics
        self._markdown = ParsedDocumentMarkdownRenderer()
        self._log = structlog.get_logger(__name__)
        self.router = APIRouter(prefix=self.PREFIX)
        self._register_routes()

    def _register_routes(self) -> None:
        self.router.add_api_route(
            "",
            self.submit_job,
            methods=["POST"],
            status_code=HTTPStatus.ACCEPTED,
            response_model=ParseJobSubmittedResponse,
        )
        self.router.add_api_route(
            "/{job_id}", self.job_status, methods=["GET"], response_model=ParseJobStatusResponse
        )
        self.router.add_api_route("/{job_id}/result", self.result_json, methods=["GET"])
        self.router.add_api_route("/{job_id}/result.md", self.result_markdown, methods=["GET"])
        self.router.add_api_route("/{job_id}/retry", self.retry_job, methods=["POST"])
        self.router.add_api_route(
            "/{job_id}", self.delete_job, methods=["DELETE"], status_code=HTTPStatus.NO_CONTENT
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

    async def result_json(self, job_id: str) -> Response:
        """Return the completed ParsedDocument JSON artifact."""
        result = await run_in_threadpool(
            self._dependencies.get_parse_job_result.execute, self._job_id(job_id)
        )
        if result.is_err:
            raise ApiError(result.unwrap_err())
        return Response(result.unwrap(), media_type="application/json")

    async def result_markdown(self, job_id: str) -> Response:
        """Return a Markdown rendering of the completed ParsedDocument."""
        result = await run_in_threadpool(
            self._dependencies.get_parse_job_result.execute, self._job_id(job_id)
        )
        if result.is_err:
            raise ApiError(result.unwrap_err())
        markdown = self._markdown.render(result.unwrap())
        return Response(markdown, media_type="text/markdown; charset=utf-8")

    async def retry_job(self, request: Request, job_id: str) -> JSONResponse:
        """Retry a failed job and return its queued state."""
        result = await run_in_threadpool(
            self._dependencies.retry_parse_job.execute, self._job_id(job_id)
        )
        if result.is_err:
            raise self._submission_error(result.unwrap_err())
        submitted = result.unwrap()
        body = ParseJobSubmittedResponse.of(submitted).model_dump(mode="json")
        location = str(request.url_for(self.job_status.__name__, job_id=submitted.job_id.value))
        return JSONResponse(
            body, status_code=HTTPStatus.ACCEPTED, headers={HttpHeader.LOCATION.value: location}
        )

    async def delete_job(self, job_id: str) -> Response:
        """Delete the job and all its stored artifacts."""
        result = await run_in_threadpool(
            self._dependencies.delete_parse_job.execute, self._job_id(job_id)
        )
        if result.is_err:
            raise ApiError(result.unwrap_err())
        return Response(status_code=HTTPStatus.NO_CONTENT)

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
