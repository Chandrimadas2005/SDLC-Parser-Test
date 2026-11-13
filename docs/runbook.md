# Parser Service runbook

How to run, configure, watch and fix the service. For local setup see
`docs/LOCAL_DEVELOPMENT.md`; for the API see the Postman collection in `docs/postman/`.

## Start and stop

| Where | Start | Stop |
|---|---|---|
| Docker | `docker compose up -d` (PostgreSQL, API, worker) | `docker compose down` |
| Local | `uv run parser-api` and, in a second terminal, `uv run parser-worker` | `Ctrl+C` in each |

The worker finishes the jobs it is running before it stops (`SIGTERM` or `Ctrl+C`).
Jobs left `running` by a crash are put back in the queue when the worker starts again.

Formats that need system tools are only offered when the tool is installed (the Docker
image has both): DOC, RTF, ODT, PPT (and the ODS fallback) need LibreOffice; PNG, JPEG,
TIFF and scanned PDF pages need Tesseract. `GET /v1/formats` shows what is available.

## Health

| Check | Meaning |
|---|---|
| `GET /health/live` = 200 | The API process is up |
| `GET /health/ready` = 200 | Database, artifact storage and free disk are fine; 503 lists what is not |
| `GET /metrics` | Submissions, outcomes and queue counters |
| Worker log `worker_started ... slots=N` | The worker is up and parses N files at once |

## Settings

All are environment variables; blank or unset means the default.

| Variable | Default | What it limits |
|---|---|---|
| `PARSER_DATABASE_URL` | local SQLite | Job database (PostgreSQL in Docker) |
| `PARSER_ARTIFACT_ROOT` | `var/artifacts` | Where uploads and results are stored |
| `PARSER_LOG_LEVEL` | `INFO` | Log detail (structured JSON; document content is never logged) |
| `PARSER_HTTP_HOST`, `PARSER_HTTP_PORT` | `0.0.0.0`, `8000` | API address |
| `PARSER_MAX_FILE_SIZE_BYTES` | 100 MB | Upload size; above it `413 file_too_large` |
| `PARSER_MAX_PAGES` | 2,000 | PDF pages; above it `file_too_large` |
| `PARSER_JOB_TIMEOUT_SECONDS` | 300 | Time per file; then `timeout` |
| `PARSER_JOB_MEMORY_LIMIT_MB` | 2,048 (1,024 in Docker) | Memory per file; then `extractor_crash` |
| `PARSER_WORKER_CONCURRENCY` | from memory | Files parsed at once by one worker |
| `PARSER_MAX_ATTEMPTS` | 3 | Automatic retries; then `max_attempts_exceeded` |
| `PARSER_QUEUE_CAPACITY` | 500 | Waiting jobs; above it `429` with `Retry-After` |
| `PARSER_MAX_BATCH_FILES` | 20 | Files in one upload; above it `413 batch_too_large` |
| `PARSER_MIN_FREE_DISK_BYTES` | 2 GB | Below it uploads get `503 disk_full` |
| `PARSER_RETENTION_DAYS` | 30 | Older files, results and jobs are deleted |
| `PARSER_ARCHIVE_MAX_DEPTH`, `_MAX_FILES`, `_MAX_EXPANDED_BYTES` | 3, 1,000, 1 GB | ZIP nesting and size (worker uses the defaults for now) |

## Scaling

One worker parses `PARSER_WORKER_CONCURRENCY` files at once; without the setting it
uses (available memory - 512 MB) / `PARSER_JOB_MEMORY_LIMIT_MB`. For more throughput
run more worker containers (`docker compose up -d --scale worker=3`): the database
queue hands every job to exactly one of them.

## When a job fails

`GET /v1/parse-jobs/{id}` shows `failure_reason`; `GET /v1/parse-jobs?status=failed`
lists all failed jobs.

| Reason | Usual cause | What to do |
|---|---|---|
| `unsupported_type` | Format not supported, or its tool is not installed | Check `/v1/formats`; install LibreOffice or Tesseract |
| `corrupted_file` | Broken file that repair could not recover | Ask for a fresh copy |
| `password_protected` | Encrypted file | Upload it again with the `password` field (PDF) |
| `file_too_large`, `limit_exceeded` | Above a size, page or archive limit | Split the file or raise the setting |
| `timeout`, `extractor_crash` | Very large or hostile file | Retried automatically; check memory and time limits |
| `max_attempts_exceeded` | Failed on every attempt | Fix the cause, then `POST /v1/parse-jobs/{id}/retry` |
| `storage_error`, `storage_permanent_error` | Disk or database problem | Check `/health/ready`, free disk, database |

## Routine tasks

- **Upgrade:** pull the new image or code, then start the API; database migrations
  run on start (forward and backward migrations are tested in CI).
- **Free disk:** old files are removed after `PARSER_RETENTION_DAYS`; delete a job and
  its files at once with `DELETE /v1/parse-jobs/{id}`.
- **Re-parse after a parser upgrade:** results are kept per parser version, so
  uploading the same file again after a version change parses it again.
- **Secrets:** passwords sent for encrypted files are stored next to the file only
  until the worker has used them, then deleted, and are never logged.
