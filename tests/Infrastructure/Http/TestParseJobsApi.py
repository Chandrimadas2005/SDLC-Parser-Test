from http import HTTPStatus

from ParserService.Domain.Errors import JobQueueError
from ParserService.Domain.Jobs import JobStatus
from tests.Infrastructure.Http.conftest import MAX_FILE_SIZE, ApiHarness

PATH = "/v1/parse-jobs"


class TestParseJobsApi:
    """Submit returns 202 and a pollable job; every error uses the envelope."""

    @staticmethod
    def _submit(harness: ApiHarness, content: bytes, name: str = "notes.txt") -> object:
        return harness.client.post(PATH, files={"file": (name, content, "text/plain")})

    def test_submit_returns_202_with_job_id_location_and_request_id(
        self, harness: ApiHarness
    ) -> None:
        response = harness.client.post(PATH, files={"file": ("notes.txt", b"hello", "text/plain")})

        assert response.status_code == HTTPStatus.ACCEPTED
        body = response.json()
        assert body["status"] == JobStatus.QUEUED
        assert body["already_existed"] is False
        assert response.headers["Location"].endswith(f"{PATH}/{body['job_id']}")
        assert response.headers["X-Request-ID"]
        assert harness.queue.depth() == 1

    def test_repeat_submission_returns_the_same_job(self, harness: ApiHarness) -> None:
        first = harness.client.post(PATH, files={"file": ("a.txt", b"same", "text/plain")}).json()

        second = harness.client.post(PATH, files={"file": ("b.txt", b"same", "text/plain")}).json()

        assert second["job_id"] == first["job_id"]
        assert second["already_existed"] is True

    def test_status_reflects_the_record(self, harness: ApiHarness) -> None:
        job_id = harness.client.post(PATH, files={"file": ("a.txt", b"x", "text/plain")}).json()[
            "job_id"
        ]

        response = harness.client.get(f"{PATH}/{job_id}")

        assert response.status_code == HTTPStatus.OK
        body = response.json()
        assert body["job_id"] == job_id
        assert body["status"] == JobStatus.QUEUED
        assert body["failure_reason"] is None
        assert body["created_at"] == 42_000
        assert body["has_result"] is False
        assert body["parser_version"] == "0.1.0-test"

    def test_unknown_job_is_404_with_the_envelope(self, harness: ApiHarness) -> None:
        response = harness.client.get(
            f"{PATH}/00000000-0000-4000-8000-00000000dead", headers={"X-Request-ID": "trace-1"}
        )

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json() == {
            "code": "job_not_found",
            "message": "No parse job has this identifier.",
            "request_id": "trace-1",
        }
        assert response.headers["X-Request-ID"] == "trace-1"

    def test_malformed_job_id_is_400(self, harness: ApiHarness) -> None:
        response = harness.client.get(f"{PATH}/not-a-uuid")

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.json()["code"] == "invalid_request"

    def test_missing_file_field_is_400(self, harness: ApiHarness) -> None:
        response = harness.client.post(PATH, data={"other": "x"})

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.json()["code"] == "invalid_request"

    def test_oversized_file_is_413_and_nothing_is_stored(self, harness: ApiHarness) -> None:
        response = harness.client.post(
            PATH,
            files={"file": ("big.bin", b"x" * (MAX_FILE_SIZE + 1), "application/octet-stream")},
        )

        assert response.status_code == HTTPStatus.REQUEST_ENTITY_TOO_LARGE
        assert response.json()["code"] == "file_too_large"
        assert harness.store.artifacts == {}
        assert harness.repository.jobs == {}

    def test_full_queue_is_429_with_retry_after(self, harness: ApiHarness) -> None:
        harness.queue.capacity = 0

        response = harness.client.post(PATH, files={"file": ("a.txt", b"x", "text/plain")})

        assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS
        assert response.json()["code"] == "queue_full"
        assert response.headers["Retry-After"] == "30"

    def test_unavailable_queue_is_503(self, harness: ApiHarness) -> None:
        harness.queue.failure = JobQueueError.QUEUE_UNAVAILABLE

        response = harness.client.post(PATH, files={"file": ("a.txt", b"x", "text/plain")})

        assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
        assert response.json()["code"] == "storage_unavailable"

    def test_metrics_count_submissions_by_outcome(self, harness: ApiHarness) -> None:
        harness.client.post(PATH, files={"file": ("a.txt", b"one", "text/plain")})
        harness.client.post(PATH, files={"file": ("a.txt", b"one", "text/plain")})

        scrape = harness.client.get("/metrics")

        assert scrape.status_code == HTTPStatus.OK
        assert 'parser_job_submissions_total{outcome="created"} 1.0' in scrape.text
        assert 'parser_job_submissions_total{outcome="existing"} 1.0' in scrape.text
