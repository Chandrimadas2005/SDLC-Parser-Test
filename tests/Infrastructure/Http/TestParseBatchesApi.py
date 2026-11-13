from http import HTTPStatus

from ParserService.Application.UseCases import ArtifactKeys
from ParserService.Domain.Jobs import FailureReason, Instant, JobCompletion, JobId, JobStatus
from tests.Infrastructure.Http.conftest import ApiHarness

PATH = "/v1/parse-jobs"
BATCHES = "/v1/parse-batches"
RESULT = b'{"status":"succeeded","document":{"file_name":"a.txt"},"elements":[]}'


class TestParseBatchesApi:
    """Several files in one upload: one job each, a batch status and a combined result."""

    @staticmethod
    def _upload(harness: ApiHarness, *names: str) -> dict[str, object]:
        files = [("file", (name, f"synthetic {name}".encode(), "text/plain")) for name in names]
        response = harness.client.post(PATH, files=files)
        assert response.status_code == HTTPStatus.ACCEPTED
        body: dict[str, object] = response.json()
        return body

    @staticmethod
    def _finish(harness: ApiHarness, job_id: str, *, succeeded: bool) -> None:
        job = harness.repository.get(JobId(job_id))
        assert job is not None
        running = job.start(Instant(43_000))
        if not succeeded:
            harness.repository.update(running.fail(FailureReason.CORRUPTED_FILE, Instant(44_000)))
            return
        pointer = ArtifactKeys().result_json(job.key.file_hash, job.key.parser_version)
        harness.store.put(pointer, RESULT)
        done = JobCompletion(JobStatus.SUCCEEDED, pointer, 0)
        harness.repository.update(running.complete(done, Instant(44_000)))

    def test_one_file_still_gives_a_single_job(self, harness: ApiHarness) -> None:
        body = self._upload(harness, "a.txt")

        assert "job_id" in body
        assert "batch_id" not in body

    def test_several_files_give_a_batch_that_is_running(self, harness: ApiHarness) -> None:
        body = self._upload(harness, "a.txt", "b.txt")
        files = body["files"]
        assert isinstance(files, list)

        status = harness.client.get(f"{BATCHES}/{body['batch_id']}")
        result = harness.client.get(f"{BATCHES}/{body['batch_id']}/result")

        assert [file["file_name"] for file in files] == ["a.txt", "b.txt"]
        assert status.json()["status"] == "running"
        assert result.status_code == HTTPStatus.CONFLICT

    def test_combined_result_has_every_file(self, harness: ApiHarness) -> None:
        body = self._upload(harness, "a.txt", "b.txt")
        files = body["files"]
        assert isinstance(files, list)
        self._finish(harness, files[0]["job_id"], succeeded=True)
        self._finish(harness, files[1]["job_id"], succeeded=False)

        combined = harness.client.get(f"{BATCHES}/{body['batch_id']}/result").json()

        first, second = combined["files"]
        assert combined["status"] == "partial"
        assert first["result"]["status"] == "succeeded"
        assert second["failure_reason"] == "corrupted_file"

    def test_refused_files_are_reported_and_limits_apply(self, harness: ApiHarness) -> None:
        big = ("file", ("big.txt", b"x" * 100, "text/plain"))
        small = ("file", ("small.txt", b"synthetic", "text/plain"))
        mixed = harness.client.post(PATH, files=[big, small]).json()
        too_many = harness.client.post(PATH, files=[small] * 4)

        assert mixed["files"][0]["error"] == "file_too_large"
        assert "job_id" in mixed["files"][1]
        assert too_many.status_code == HTTPStatus.REQUEST_ENTITY_TOO_LARGE
        assert too_many.json()["code"] == "batch_too_large"

    def test_unknown_batch_is_not_found(self, harness: ApiHarness) -> None:
        missing = harness.client.get(f"{BATCHES}/7d1f0f4e-3c43-4c55-9b33-2f6f3d0a9c10")
        malformed = harness.client.get(f"{BATCHES}/not-a-batch")

        assert missing.status_code == HTTPStatus.NOT_FOUND
        assert malformed.status_code == HTTPStatus.NOT_FOUND
