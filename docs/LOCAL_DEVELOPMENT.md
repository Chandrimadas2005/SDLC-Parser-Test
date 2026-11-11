# Run the Parser Service locally

## 1. Prepare WSL Ubuntu

The repository targets Python 3.12. Install the system library used by `python-magic`:

```bash
sudo apt update
sudo apt install -y libmagic1 git unzip
```

Install `uv` if it is not already available:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env"
```

## 2. Resolve and install dependencies

From the repository root, refresh the lock for the spreadsheet dependencies and install
Python 3.12 plus runtime and development dependencies:

```bash
uv lock
uv sync
```

The runtime spreadsheet dependencies are `openpyxl` (XLSX/XLSM) and `xlrd` (legacy XLS).

## 3. Install and run repository checks

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```

Run the test suite directly when needed:

```bash
uv run pytest
```

## 4. Start the service

For the standalone Docker deployment:

```bash
docker compose up --build
```

For local development without Docker, copy the optional environment file and use two
terminals. SQLite is the local-development database default:

```bash
cp .env.example .env
uv run parser-api
```

In a second terminal:

```bash
uv run parser-worker
```

The API listens at `http://127.0.0.1:8000`; interactive API docs are at
`http://127.0.0.1:8000/docs`.

## 5. Submit and retrieve a file

Submit a synthetic file (for example, a local workbook):

```bash
curl -F "file=@tests/corpus/xlsx/normal/normal.xlsx" http://127.0.0.1:8000/v1/parse-jobs
```

Copy the returned `job_id`, then poll until the status is `succeeded` or `partial`:

```bash
curl http://127.0.0.1:8000/v1/parse-jobs/<job_id>
```

Retrieve the JSON or Markdown result:

```bash
curl http://127.0.0.1:8000/v1/parse-jobs/<job_id>/result
curl http://127.0.0.1:8000/v1/parse-jobs/<job_id>/result.md
```

Other management endpoints:

```bash
curl -X POST http://127.0.0.1:8000/v1/parse-jobs/<job_id>/retry
curl -X DELETE http://127.0.0.1:8000/v1/parse-jobs/<job_id>
curl http://127.0.0.1:8000/v1/formats
```

`retry` is accepted only for failed jobs. `DELETE` removes the source file, result artifact
and job record. The formats endpoint reports the parser version and currently registered
formats.

## 6. Spreadsheet corpus and known limitation

Synthetic spreadsheet fixtures and their golden JSON files live under `tests/corpus/` and
`tests/golden/extraction/`. Regenerate XLSX fixtures with:

```bash
uv run python tests/corpus/xlsx/WorkbookCorpusGenerator.py
```

Regenerate XLS fixtures with LibreOffice installed:

```bash
uv run python tests/corpus/xls/XlsCorpusGenerator.py
```

`xlrd` does not expose formula expressions for legacy XLS files. The XLS extractor keeps
available cached values and merged ranges, but formula expressions are not available;
this is recorded as an open point in `docs/spreadsheet-extraction.md`.
