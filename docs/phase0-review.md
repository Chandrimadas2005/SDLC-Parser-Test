# Phase 0 review: proposals from track A (jobs, storage, data formats)

The brief asks the Phase 0 review to settle the queue, the default limits, the retention
default and the storage split, and to propose phase durations. This page is track A's input.

## 1. Queue: PostgreSQL-based (proposed)

The brief allows a Valkey-based or a PostgreSQL-based queue. We propose PostgreSQL.

**How it works.** The job table is the queue. A job is queued when its row has status
`queued`. A worker claims the oldest queued row with `SELECT ... FOR UPDATE SKIP LOCKED`,
moves it to `running` and increments the attempt counter in the same transaction, so two
workers never take the same job. Implementation: `PostgresJobQueue`.

**Why.**

- One stateful service instead of two. `docker compose up` starts PostgreSQL and the API,
  nothing else. There is one thing to back up, monitor and secure.
- Restart recovery is free (brief 2.5, "restart during a job"). Jobs are rows; a job that was
  running when the process died is still a row and can be returned to `queued` on start-up.
- The bounded queue is a row count (brief 2.5, "too many jobs"). `429` with `Retry-After` when
  the count exceeds `PARSER_QUEUE_CAPACITY`.
- Idempotency and the queue share one transaction boundary: the unique
  `(file_hash, parser_version)` constraint and the enqueue cannot disagree.
- Throughput is not the bottleneck. Parsing a file takes seconds; claiming a row takes
  milliseconds. `SKIP LOCKED` scales to tens of workers comfortably.

**When to revisit.** If the service must handle thousands of jobs per minute or several
hundred concurrent workers, a Valkey (BSD-3) stream behind the same `JobQueue` port is a
drop-in change. Nothing in Domain or Application would move.

## 2. Default limits (proposed, settings in `Limits`)

All of these are environment variables (see `.env.example`); nothing is hard-coded. The
values are deliberately conservative until track B's measurement script has run on the
corpus. They should be re-proposed with measured numbers at the Phase 1 review.

| Setting | Default | Reasoning |
|---|---|---|
| `PARSER_MAX_FILE_SIZE_BYTES` | 100 MiB | Covers large spreadsheets and scanned PDFs; above this, streaming and OCR time dominate |
| `PARSER_MAX_PAGES` | 2 000 | OCR at roughly 1 to 3 s per page keeps a worst case inside the timeout |
| `PARSER_JOB_TIMEOUT_SECONDS` | 300 | Kill a hung extractor after five minutes |
| `PARSER_JOB_MEMORY_LIMIT_MB` | 2 048 | Per-job subprocess ceiling; the container has 2 GiB in compose |
| `PARSER_ARCHIVE_MAX_DEPTH` | 3 | Archive inside archive inside archive is enough for real mail attachments |
| `PARSER_ARCHIVE_MAX_FILES` | 1 000 | Caps fan-out of a single ZIP |
| `PARSER_ARCHIVE_MAX_EXPANDED_BYTES` | 1 GiB | Stops zip bombs: 10x the file size limit |
| `PARSER_MAX_ATTEMPTS` | 3 | Then the job stays in the failed-jobs store for manual retry |
| `PARSER_QUEUE_CAPACITY` | 500 | Memory stays flat because queued jobs are rows, not buffers |
| `PARSER_MIN_FREE_DISK_BYTES` | 2 GiB | `/health/ready` turns not-ready below this and new jobs are refused |

## 3. Retention default: 30 days (proposed)

Original files and results are removed by a cleanup task after `PARSER_RETENTION_DAYS`
(default 30). Reasoning: callers poll within minutes and fetch results within days;
thirty days gives room for re-reads and audits without storing customer files forever.
The job record stays after the files are removed so a later identical upload still
reports that a result once existed and reparses cleanly. Delete through the API removes
everything at once, regardless of retention.

## 4. Storage split (brief 2.7)

| Data | Where | Pointer |
|---|---|---|
| Original file | `ArtifactStore`, key `files/<h2>/<sha256>/original<ext>` | `jobs.file_pointer` |
| Result JSON | `ArtifactStore`, key `results/<h2>/<sha256>/<parser_version>/result.json` | `jobs.result_pointer` |
| Result Markdown | `ArtifactStore`, same folder, `result.md` | derived from `result_pointer` |
| Job record | PostgreSQL schema `parser`, table `jobs` | |

Keys are derived from the SHA-256 digest, never from the caller's file name, so no customer
name leaks into storage paths and two uploads of the same bytes share one copy. The
database never holds content: identifiers, hashes, counts, timings and pointers only.

Write order on completion: result file first, then job record. If the process stops in
between, the next run overwrites the file and finishes cleanly (brief 2.7, "safe to repeat").

## 5. Proposed phase durations (track A)

| Phase | Duration | Note |
|---|---|---|
| 0 Foundation | 1 week | This review closes it |
| 1 Spreadsheets | 3 weeks | XLSX streaming and header detection are the risky parts |
| 2 Documents (track B, parallel) | 3 weeks | |
| 3 Fault tolerance | 2 weeks | Most of the plumbing (worker, queue, retries) exists after Phases 0 to 2 |
| 4 More formats | 2 weeks | |
| 5 Finish | 1 week | Docs, runbook, CLI |

## 6. Deviations from the brief, for the lead to confirm

- **`file_name` column.** The brief's job record list does not include the caller's file
  name. The worker needs it for `document.file_name` in the `ParsedDocument`, so it is
  stored in the job row (metadata, not content). Alternative: store it beside the file.
- **Extra packages.** `Infrastructure/Bootstrap` (composition root, process entry point)
  and `Infrastructure/Time` (clock adapter) are not in the brief's package list but have
  no other natural home.
- **Alembic script shape.** Alembic requires module-level `upgrade`/`downgrade` names in
  version files and a script `env.py`. Version files define one class and bind the two
  names to its methods (no top-level `def`). `env.py` is a one-line delegation and is
  exempted in the code-rules checker.
- **PostgreSQL tests locally.** The developer machine has no Docker. The database tests run
  on SQLite locally and on both SQLite and a real PostgreSQL service in CI.

## 7. Open questions for the review

1. Should a repeated upload with an existing `failed` job return the failed job (current
   behaviour: yes, so the caller sees the reason) or start a new attempt automatically?
2. Is the queue capacity measured as queued rows only, or queued plus running?
3. May the result Markdown share the JSON pointer (derived path) or should it be its own
   column?
