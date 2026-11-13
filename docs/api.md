# Parser Service API

Base URL for local development: `http://localhost:8000`. The interactive OpenAPI
reference is served at `/docs` by FastAPI. The shared request examples and executable
checks are in [`postman/parser-service.postman_collection.json`](postman/parser-service.postman_collection.json).

All uploads use `multipart/form-data`. Errors raised by the registered API endpoints use
the common envelope below.
The API is asynchronous: submit a file, poll its job, then retrieve its result. Times
in job responses are UTC epoch milliseconds.

## Submit and inspect parse jobs

### `POST /v1/parse-jobs`

Submit one file, or multiple files in one request. The multipart request has one or
more `file` fields (the field name is repeated for each file) and an optional `password`
text field. `password` is intended for encrypted PDFs. It is not included in logs; the
service holds it only until the worker attempts the parse and then removes it. When a
password is supplied for a file that previously failed as `password_protected`, that
file can be submitted again with the password.

A single-file response is `202 Accepted`:

```json
{
  "job_id": "a5d3aaf0-1a2b-4d9c-8f02-9f8a0b1a2345",
  "status": "queued",
  "already_existed": false
}
```

`already_existed` is true when the same file hash and parser version already have a
job. In that case the existing job/result is returned instead of creating duplicate
work. The response includes a `Location` header for the job status resource. Job states are
`queued`, `running`, `succeeded`, `partial`, `failed` or `deleting`.

For multiple `file` fields, the same endpoint returns a batch response:

```json
{
  "batch_id": "b5d3aaf0-1a2b-4d9c-8f02-9f8a0b1a2345",
  "files": [
    {"file_name": "first.txt", "job_id": "a5d3aaf0-1a2b-4d9c-8f02-9f8a0b1a2345", "status": "queued", "already_existed": false},
    {"file_name": "second.json", "job_id": "c5d3aaf0-1a2b-4d9c-8f02-9f8a0b1a2345", "status": "queued", "already_existed": false}
  ]
}
```

When some files are accepted and others are refused, the batch is still accepted and
the refused file entry carries an `error` code instead of a job ID. If no file is
accepted, the first submission error is returned as the HTTP error envelope.

Success: `202`. Errors: `400 invalid_request`, `413 file_too_large` or
`batch_too_large`, `429 queue_full` (includes `Retry-After`), `503 disk_full` or
`storage_unavailable`.

### `GET /v1/parse-jobs/{id}`

Get job state, attempts, failure reason, warning count and timestamps. Example:

```json
{
  "job_id": "a5d3aaf0-1a2b-4d9c-8f02-9f8a0b1a2345",
  "status": "succeeded",
  "parser_version": "0.1.0",
  "failure_reason": null,
  "attempt_count": 1,
  "warning_count": 0,
  "has_result": true,
  "created_at": 1794591000000,
  "started_at": 1794591000100,
  "finished_at": 1794591000200,
  "duration_ms": 100
}
```

Success: `200`. Errors: `400 invalid_request` for a malformed ID; `404 job_not_found`
for an unknown ID.

### `GET /v1/parse-jobs/{id}/result`

Return the completed `ParsedDocument` as JSON (schema version 1.2). A complete response
example is [`txt_notes.json`](../tests/golden/extraction/txt_notes.json). Success: `200`
with `application/json`. Errors: `400 invalid_request`, `404 job_not_found` or
`result_not_found`, `409 result_not_ready` while the job is queued or running, `409 job_failed`
when the job failed (it will never have a result; read `failure_reason` from the job status).

### `GET /v1/parse-jobs/{id}/result.md`

Return the same parsed result rendered as Markdown. Example body:

```markdown
# Parsed document

**File:** notes.txt
**Status:** succeeded

## Outline

## Warnings

## Elements

### paragraph

Synthetic meeting notes for parser tests.
They contain no real data.

### paragraph

The second paragraph has two lines
that belong together.

### paragraph

Last paragraph.
```

Success: `200` with `text/markdown; charset=utf-8`. Errors: `400 invalid_request`, `404 job_not_found` or
`result_not_found`, `409 result_not_ready` while the job is queued or running, `409 job_failed`
when the job failed (it will never have a result; read `failure_reason` from the job status).

### `POST /v1/parse-jobs/{id}/retry`

Requeue a failed job. No request body is required. Success: `202` with the submitted
job response (`job_id`, `status`, `already_existed`), for example:

```json
{"job_id":"a5d3aaf0-1a2b-4d9c-8f02-9f8a0b1a2345","status":"queued","already_existed":false}
```

Errors: `400 invalid_request`,
`404 job_not_found`, `409 retry_not_allowed`, `429 queue_full`, `503 storage_unavailable`.

### `DELETE /v1/parse-jobs/{id}`

Delete the original file, parsed JSON and Markdown artifacts, and job record together.
No request body is required. Success: `204 No Content` with an empty response body. Errors: `400 invalid_request`,
`404 job_not_found`, `503 storage_unavailable`.

### `GET /v1/parse-jobs?status=failed`

List persisted failed jobs. The `status` query parameter defaults to `failed`; any
other value is rejected. Success: `200` with an array of job-status objects (the same
shape as `GET /v1/parse-jobs/{id}`), for example `[]` when there are no failures.
Error: `400 invalid_request`.

## Multi-file batches

### `GET /v1/parse-batches/{id}`

Get the overall batch status and every file's job status. Example:

```json
{
  "batch_id": "b5d3aaf0-1a2b-4d9c-8f02-9f8a0b1a2345",
  "status": "running",
  "files": [
    {"file_name": "first.txt", "job_id": "a5d3aaf0-1a2b-4d9c-8f02-9f8a0b1a2345", "status": "succeeded"},
    {"file_name": "second.json", "job_id": "c5d3aaf0-1a2b-4d9c-8f02-9f8a0b1a2345", "status": "running"}
  ]
}
```

Success: `200`. Error: `404 batch_not_found` for an unknown or malformed batch ID.

### `GET /v1/parse-batches/{id}/result`

Return one combined JSON response with each file's `result` (a parsed document) or
`failure_reason`. Example response for a batch with one failed file:

```json
{"batch_id":"b5d3aaf0-1a2b-4d9c-8f02-9f8a0b1a2345","status":"partial","files":[{"file_name":"broken.txt","job_id":"a5d3aaf0-1a2b-4d9c-8f02-9f8a0b1a2345","status":"failed","failure_reason":"corrupted_file"}]}
```

Success: `200` when all files are terminal. Errors: `404 batch_not_found`,
`409 result_not_ready` until every file has finished.

## Formats, health and metrics

| Method and path | Purpose | Success response | Error responses |
|---|---|---|---|
| `GET /v1/formats` | Registered formats and parser version | `200` `{"parser_version":"0.1.0","formats":["xlsx","xlsm","xls","csv","tsv","pdf","docx","txt","md","pptx","html","ods","eml","msg","zip","json","yaml","xml"]}` (optional system-tool formats may also appear) | None expected |
| `GET /health/live` | Process liveness | `200` `{"status":"live"}` | None expected |
| `GET /health/ready` | Database, artifact storage and disk readiness | `200` `{"status":"ready"}` | `503 not_ready` |
| `GET /metrics` | Prometheus metrics | `200` Prometheus exposition text | None expected |

The `formats` array contains only formats with a registered extractor and may depend
on optional system tools (see the runbook). Liveness and readiness examples are
`{"status":"live"}` and `{"status":"ready"}` respectively. The metrics response is
Prometheus text, for example `parser_queue_depth 0.0`.

## Error envelope

Every handled API error has the same JSON shape and echoes the `X-Request-ID` response header.
The request ID is taken from the incoming `X-Request-ID` header when supplied, or
created by the service.

```json
{
  "code": "job_not_found",
  "message": "No parse job has this identifier.",
  "request_id": "d4f09c9a-bb5f-4d0c-a03d-9e8c43a1c1a1"
}
```

| HTTP status | Error codes | Meaning |
|---|---|---|
| `400` | `invalid_request` | Malformed request, identifier or query parameter |
| `404` | `job_not_found`, `batch_not_found`, `result_not_found` | Requested resource is absent |
| `409` | `result_not_ready`, `job_failed`, `retry_not_allowed` | Result is not ready yet, the job failed and has no result, or the job cannot be retried in its current state |
| `413` | `file_too_large`, `batch_too_large` | Upload exceeds configured size or batch count |
| `429` | `queue_full` | Queue is full; response includes `Retry-After` |
| `503` | `disk_full`, `storage_unavailable`, `not_ready` | Storage, free disk or readiness dependency is unavailable |
| `500` | `internal_error` | Unexpected server-side failure |

Parsing failures are reported on the job status/result as `failure_reason`, not as an
HTTP error from the submission call. The parser failure reasons include
`unsupported_type`, `corrupted_file`, `password_protected`, `file_too_large`,
`limit_exceeded`, `timeout`, `extractor_crash`, `max_attempts_exceeded`, `storage_error`
and `storage_permanent_error`.

## Operational limits

The following are the defaults documented in [`runbook.md`](runbook.md). Environment
variables can override the configurable values.

| Setting | Default | Behaviour when exceeded |
|---|---:|---|
| `PARSER_MAX_FILE_SIZE_BYTES` | 100 MB | Reject with `413 file_too_large` |
| `PARSER_MAX_PAGES` | 2,000 | Reject with `file_too_large` |
| `PARSER_JOB_TIMEOUT_SECONDS` | 300 seconds | Kill timed-out worker; failure reason `timeout` |
| `PARSER_JOB_MEMORY_LIMIT_MB` | 2,048 MB (1,024 MB in Docker) | Worker isolation; failure reason `extractor_crash` |
| `PARSER_WORKER_CONCURRENCY` | Derived from available memory | Limits files parsed concurrently by one worker |
| `PARSER_MAX_ATTEMPTS` | 3 | Then `max_attempts_exceeded` and manual retry is available |
| `PARSER_QUEUE_CAPACITY` | 500 waiting jobs | `429 queue_full` with `Retry-After` |
| `PARSER_MAX_BATCH_FILES` | 20 | Reject with `413 batch_too_large` |
| `PARSER_MIN_FREE_DISK_BYTES` | 2 GB | Reject uploads with `503 disk_full`; readiness is false |
| `PARSER_RETENTION_DAYS` | 30 days | Older files, results and jobs are cleaned up |
| `PARSER_ARCHIVE_MAX_DEPTH` | 3 | Reject excessive nesting with `limit_exceeded` |
| `PARSER_ARCHIVE_MAX_FILES` | 1,000 | Reject excessive file count with `limit_exceeded` |
| `PARSER_ARCHIVE_MAX_EXPANDED_BYTES` | 1 GB | Reject excessive expanded size with `limit_exceeded` |
| `PARSER_STRUCTURED_MAX_DEPTH` | 32 | JSON, YAML or XML nested deeper fails with `limit_exceeded` |
| `PARSER_STRUCTURED_MAX_NODES` | 100,000 | JSON, YAML or XML with more values (including expanded YAML aliases) fails with `limit_exceeded` |

The isolated worker process inherits the same environment, so every limit above also
applies inside it. How JSON, YAML and XML become elements is described in
[`structured-data-extraction.md`](structured-data-extraction.md). Database
configuration, artifact paths and HTTP host/port are also controlled by the environment;
see the runbook for their variable names.
