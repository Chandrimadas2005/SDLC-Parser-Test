from fastapi import APIRouter
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from ParserService.Application.Errors.ApplicationErrorCode import ApplicationErrorCode
from ParserService.Domain.Jobs.BatchId import BatchId
from ParserService.Infrastructure.Http.ApiDependencies import ApiDependencies
from ParserService.Infrastructure.Http.ApiError import ApiError
from ParserService.Infrastructure.Http.BatchResponse import BatchResponse


class ParseBatchesRouter:
    """Routes for files uploaded together: the batch status and the combined result."""

    def __init__(self, dependencies: ApiDependencies) -> None:
        self._batches = dependencies.get_parse_batch
        self._responses = BatchResponse()
        self.router = APIRouter(prefix="/v1/parse-batches", tags=["parse batches"])
        self.router.add_api_route("/{batch_id}", self.batch_status, methods=["GET"])
        self.router.add_api_route("/{batch_id}/result", self.batch_result, methods=["GET"])

    async def batch_status(self, batch_id: str) -> JSONResponse:
        """Every file's job status and the batch's overall status.

        Raises:
            ApiError: ``BATCH_NOT_FOUND`` (unknown or malformed identifier).
        """
        view = await run_in_threadpool(self._batches.status, self._identifier(batch_id))
        if view.is_err:
            raise ApiError(view.unwrap_err())
        return JSONResponse(self._responses.status(view.unwrap()))

    async def batch_result(self, batch_id: str) -> JSONResponse:
        """One combined JSON with every file's parsed document or failure reason.

        Raises:
            ApiError: ``BATCH_NOT_FOUND``, or ``RESULT_NOT_READY`` while any file runs.
        """
        view = await run_in_threadpool(self._batches.combined, self._identifier(batch_id))
        if view.is_err:
            raise ApiError(view.unwrap_err())
        return JSONResponse(self._responses.combined(view.unwrap()))

    @staticmethod
    def _identifier(batch_id: str) -> BatchId:
        try:
            return BatchId(batch_id)
        except ValueError as error:
            raise ApiError(ApplicationErrorCode.BATCH_NOT_FOUND) from error
