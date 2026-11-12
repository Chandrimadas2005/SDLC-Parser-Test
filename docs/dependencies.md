# Dependencies

Every dependency, its version and its licence. Versions are the ones pinned in `uv.lock`.

**Licence policy.** Only MIT, BSD, Apache-2.0, ISC or PSF licensed libraries may ship. No
GPL, LGPL or AGPL. In particular, PyMuPDF (AGPL) and psycopg (LGPL-3.0) are not used; the
PostgreSQL driver is pg8000 (BSD). Separate tools run as their own process (LibreOffice,
OCRmyPDF, Tesseract) are allowed. CI builds an environment with the runtime dependencies only
and fails if any package in it has a licence outside the list.

## Runtime

Shipped in the service image. Checked by CI.

| Package | Version | Licence | Purpose |
|---|---|---|---|
| alembic | 1.20.1 | MIT | Schema migrations, forward and backward |
| charset-normalizer | 3.5.2 | MIT | Encoding detection for text files |
| fastapi | 0.162.2 | MIT | HTTP API |
| defusedxml | 0.7.1 | PSF-2.0 | Safe XML parsing of untrusted workbook parts (brief 2.5) |
| openpyxl | 3.1.5 | MIT | Streaming XLSX/XLSM worksheet extraction |
| pg8000 | 1.31.6 | BSD-3-Clause | Pure-Python PostgreSQL driver |
| prometheus-client | 0.26.0 | Apache-2.0 | `/metrics` |
| pydantic | 2.14.3 | MIT | Request and response models |
| pypdfium2 | 5.15.2 | Apache-2.0 / BSD-3-Clause | PDF text and outline (bundles Google's PDFium); chosen in `docs/pdf-library-comparison.md` |
| python-magic | 0.4.27 | MIT | Content-based type detection (needs the libmagic1 system package) |
| python-multipart | 0.0.33 | Apache-2.0 | Multipart file uploads for FastAPI |
| sqlalchemy | 2.1.8 | MIT | Core SQL toolkit for the job table |
| structlog | 25.5.0 | MIT OR Apache-2.0 | Structured JSON logging |
| uvicorn | 0.54.0 | BSD-3-Clause | ASGI server |
| xlrd | 2.0.1 | BSD-3-Clause | Legacy XLS workbook extraction |

Transitive runtime packages (all inside the allow-list):

| Package | Version | Licence | Pulled in by |
|---|---|---|---|
| annotated-doc | 0.0.5 | MIT | fastapi |
| et-xmlfile | 2.0.0 | MIT | openpyxl |
| annotated-types | 0.8.0 | MIT | pydantic |
| anyio | 4.16.0 | MIT | starlette |
| asn1crypto | 1.5.1 | MIT | scramp |
| click | 8.5.1 | BSD-3-Clause | uvicorn |
| h11 | 0.16.0 | MIT | uvicorn |
| idna | 3.20 | BSD-3-Clause | anyio |
| Mako | 1.4.3 | MIT | alembic |
| MarkupSafe | 3.0.4 | BSD-3-Clause | Mako |
| opentelemetry-api | 1.45.2 | Apache-2.0 | fastapi |
| pydantic-core | 2.50.4 | MIT | pydantic |
| python-dateutil | 4.0.0 | BSD-3-Clause | pg8000 |
| scramp | 1.5.0 | MIT-0 | pg8000 |
| starlette | 1.10.0 | BSD-3-Clause | fastapi |
| typing-extensions | 4.16.0 | PSF-2.0 | pydantic, sqlalchemy |
| typing-inspection | 0.4.5 | MIT | pydantic |
| tzdata | 2026.6 | Apache-2.0 | alembic |

## Build

| Package | Version | Licence | Purpose |
|---|---|---|---|
| hatchling | >=1.27 | MIT | Build backend for the wheel |

## Development and CI tools

Not shipped. Used for checks, tests and local hooks.

| Package | Version | Licence | Purpose |
|---|---|---|---|
| httpx2 | 2.16.0 | BSD-3-Clause | HTTP client behind the FastAPI test client |
| import-linter | 2.16 | BSD-2-Clause | Layer rules (`Infrastructure -> Application -> Domain`) |
| jsonschema | 4.26.0 | MIT | Checks every encoded `ParsedDocument` against `schemas/parsed_document.v1.json` |
| mypy | 2.4.1 | MIT | Strict static typing (with the pydantic plugin) |
| pdfplumber | 0.11.10 | MIT | PDF library comparison only (`tools/PdfComparison`) |
| pip-audit | 2.10.1 | Apache-2.0 | Vulnerability scan |
| pip-licenses | 5.5.5 | MIT | Licence policy check |
| pre-commit | 4.7.0 | MIT | Runs the CI checks before each commit |
| pypdf | 6.21.4 | BSD-3-Clause | PDF library comparison only |
| pytest | 9.2.0 | MIT | Test runner |
| pytest-cov | 7.1.0 | MIT | Coverage |
| reportlab | 4.5.1 | BSD-3-Clause | Writes the synthetic PDFs for the comparison |
| ruff | 0.17.4 | MIT | Lint and format (complexity 4, arguments 3) |
| types-defusedxml | 0.7.0.20260504 | Apache-2.0 | Type stubs for defusedxml |
| types-jsonschema | 4.26.0.20261006 | Apache-2.0 | Type stubs for jsonschema (`mypy --strict`) |
| types-openpyxl | 3.1.5.20261017 | Apache-2.0 | Type stubs for openpyxl |
| types-reportlab | 4.5.1.20260827 | Apache-2.0 | Type stubs for reportlab |

Transitive development-only packages inside the allow-list:

| Package | Version | Licence | Pulled in by |
|---|---|---|---|
| attrs | 26.1.0 | MIT | jsonschema |
| cryptography | 50.0.2 | Apache-2.0 OR BSD-3-Clause | pdfminer.six |
| jsonschema-specifications | 2025.9.1 | MIT | jsonschema |
| pdfminer.six | 20260107 | MIT | pdfplumber |
| pycparser | 3.12 | BSD-3-Clause | cffi |
| referencing | 0.37.0 | MIT | jsonschema |
| rpds-py | 2026.9.1 | MIT | jsonschema |

Transitive development-only packages outside the shipping allow-list, never part of the
image:

| Package | Version | Licence | Pulled in by |
|---|---|---|---|
| certifi | 2026.10.23 | MPL-2.0 | pip-audit (via requests) |
| cffi | 2.1.1 | MIT-0 | cryptography (PDF comparison tool) |
| pathspec | 1.1.1 | MPL-2.0 | mypy |
| pillow | 13.0.0 | MIT-CMU | pdfplumber (PDF comparison tool); needs approval before pdfplumber could ship |

## System packages in the image

| Package | Source | Licence | Purpose |
|---|---|---|---|
| libmagic1 | Debian bookworm | BSD-2-Clause | Content-based type detection (python-magic, track B) |
| libreoffice-writer-nogui, libreoffice-calc-nogui, libreoffice-impress-nogui | Debian bookworm | MPL-2.0 | Converts DOC, RTF, ODT, ODS and PPT; run as a separate process |
| fonts-dejavu-core | Debian bookworm | Bitstream Vera / public domain | Fonts LibreOffice needs to lay out documents |
