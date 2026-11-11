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
tools/             Repository tooling (code-rule checks); not shipped
docs/              Dependencies, Phase 0 review proposals
```

Dependencies point inward only: `Infrastructure -> Application -> Domain`.
`import-linter` enforces this in CI.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the code rules, branch naming, commit format
and the review process. Nothing is merged to the default branch without lead review.
