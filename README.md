# Parser Service

A standalone service that reads files and returns clean, structured data, with every
piece of data linked back to where it came from in the file.

The service has its own API, output format (`ParsedDocument`), database schema and
tests. It runs with one command and needs nothing else to work:

```bash
docker compose up
```

Then submit a file and poll the job:

```bash
curl -F "file=@notes.txt" http://localhost:8000/v1/parse-jobs
# {"job_id":"...","status":"queued","already_existed":false}
curl http://localhost:8000/v1/parse-jobs/<job_id>
```

`docker compose up` also starts the worker, which parses each queued file in its own
short-lived process with time and memory limits, so the job moves to `succeeded`.

Health and metrics: `/health/live`, `/health/ready`, `/metrics`.

To try the API without curl, import `docs/postman/parser-service.postman_collection.json`
into Postman. It holds every request with test scripts; set `baseUrl` if the service is not
on `http://localhost:8000`.

Result and management endpoints:

```bash
curl http://localhost:8000/v1/parse-jobs/<job_id>/result
curl http://localhost:8000/v1/parse-jobs/<job_id>/result.md
curl -X POST http://localhost:8000/v1/parse-jobs/<job_id>/retry
curl -X DELETE http://localhost:8000/v1/parse-jobs/<job_id>
curl http://localhost:8000/v1/formats
```

Spreadsheet support: XLSX, XLSM, XLS, CSV and TSV. XLS formula expressions are not
exposed by `xlrd`; the extractor preserves available cell values and merged ranges. See
[spreadsheet extraction notes](docs/spreadsheet-extraction.md).

## Development setup

See [local development instructions](docs/LOCAL_DEVELOPMENT.md) for WSL setup, checks, and API usage.


Requirements: [uv](https://docs.astral.sh/uv/) (it installs the pinned Python itself).

```bash
uv sync                      # resolve added spreadsheet libraries and create .venv
uv run pre-commit install    # run the same checks as CI before every commit
cp .env.example .env         # optional local overrides (SQLite by default)
uv run parser-api            # serve on http://127.0.0.1:8000 without Docker
uv run parser-worker         # in a second terminal: parse queued jobs
uv run python -m tools.Measurement tests/corpus docs/measurements.md   # parse cost per file
uv run python -m tools.PdfComparison docs/pdf-library-comparison.md    # PDF library comparison
```

Run every check that CI runs:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run lint-imports
uv run python -m tools.CodeRules src tools tests
uv run pytest
```

Database tests run on SQLite by default. Set `PARSER_TEST_DATABASE_URL` to a PostgreSQL URL
to run them against a real PostgreSQL as well (CI does this with a service container).

## Standalone CLI

`parser-cli` parses one file with the same detector, extractors and encoders as the worker,
without the web server or the database (brief, 2.4):

```bash
uv run parser-cli parse ./page.html                     # print the JSON result, save nothing
uv run parser-cli parse ./book.ods --format markdown    # print the Markdown version
uv run parser-cli parse ./book.ods --summary            # print the result, then the summary
uv run parser-cli parse ./book.ods --output ./parsed    # save parsed_document.json/.md instead
```

The optional summary is made only with `--summary` and can never fail the parse. Exit codes:
`0` succeeded, `2` partial, `1` failed. Results go to standard output; status lines and errors
go to standard error. HTML, ODS and summary details: [docs/html-ods-extraction.md](docs/html-ods-extraction.md).

## Configuration

Every setting is an environment variable named in the `EnvironmentVariable` enum and
documented in [.env.example](.env.example). Limits (file size, pages, time, memory, archive
depth, retries, queue capacity, retention, free disk) are settings, never constants in code.

## Layout

```
src/ParserService/
  Domain/          Documents, Jobs, Ports (Protocols), Errors   - no outside imports
  Application/     UseCases, Dto, Errors                        - depends on Domain only
  Infrastructure/  Extraction, Detection, Isolation, Persistence,
                   Storage, Queue, Http, Cli, Logging, Config, Time, Bootstrap,
                   Output (JSON form of a ParsedDocument)
tests/             Domain, Application, Infrastructure, Contract, FaultInjection, Fakes,
                   Samples, corpus, golden
schemas/           JSON Schema of the output format (parsed_document.v1.json)
tools/             Repository tooling (code rules, measurement, PDF comparison); not shipped
docs/              Dependencies, Phase 0 review, measurements, PDF comparison, Postman collection
```

Dependencies point inward only: `Infrastructure -> Application -> Domain`.
`import-linter` enforces this in CI.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the code rules, branch naming, commit format
and the review process. Nothing is merged to the default branch without lead review.

## Worker concurrency

One worker process parses several files at the same time, each in its own isolated
process. `PARSER_WORKER_CONCURRENCY` sets how many; when it is blank the worker uses
(available memory - 512 MB) / `PARSER_JOB_MEMORY_LIMIT_MB`, between 1 and 64, so
concurrent jobs never ask for more memory than the container has. Jobs beyond that
wait in the queue and start by themselves when a slot frees up. For more throughput,
run more worker containers: the queue hands each job to exactly one of them.

## Several files in one upload

Send two or more files in the same `file` field of `POST /v1/parse-jobs`. Each file
becomes an ordinary job (so the duplicate rule and size limit apply per file) and the
worker slots parse them in parallel. The answer is `202` with a `batch_id`;
`GET /v1/parse-batches/{batch_id}` shows every file's status, and
`GET /v1/parse-batches/{batch_id}/result` returns one combined JSON with each file's
parsed document or failure reason (`409` until every file has finished). One file in
a request behaves exactly as before. `PARSER_MAX_BATCH_FILES` (default 20) caps the
files per request.

## Password-protected files

Send the password in the optional `password` form field of `POST /v1/parse-jobs`. It
is kept next to the stored file only until the worker has used it, never logged, and
then deleted. A file that already failed as `password_protected` is parsed again when
it is uploaded with a password. PDFs are supported; encrypted Office files still fail
as `password_protected` (open point).
