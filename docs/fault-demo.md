# Breaking the service on purpose (fault-tolerance demo)

Every row of the brief's fault-tolerance table, how to trigger it during a demo and
what to show. Each one also has an automated test (`uv run pytest tests/FaultInjection`
and the tests named in the last column).

Start the API and the worker first (see `docs/runbook.md`) and use the Postman
collection (`docs/postman/`) for the uploads.

| Fault | How to trigger it | What to show | Test |
|---|---|---|---|
| Wrong extension | Upload a text file renamed `notes.pdf` | `succeeded`, type `txt`, warning `extension_mismatch` | Detection tests |
| Corrupted file | Upload a DOCX cut short (`orion-damaged.docx`) | `partial` with `file_repaired`; a hopeless file gives `corrupted_file` | TestRepairingExtractor |
| Password-protected | Upload an encrypted PDF, then again with the `password` field | First `password_protected`, then `succeeded` | TestPasswordUnlock, TestSubmitWithPassword |
| One page or sheet fails | Upload a deck with a broken slide | `partial` with `slide_unreadable` at that slide | TestPptxExtractor |
| Scanned pages | Upload a scanned PDF or a photo of text | `ocr_applied` and `ocr_confidence` | TestPdfOcr, TestImageExtractor |
| Archive or XML attack | Upload a ZIP with more than 1,000 files, or nested 6 deep | `limit_exceeded`, or `element_skipped` for the deep part | TestContainerExtractors |
| File too large | Upload a file above `PARSER_MAX_FILE_SIZE_BYTES` (set it low for the demo) | `413 file_too_large` before parsing | TestFaultTolerance |
| Hang | Set `PARSER_JOB_TIMEOUT_SECONDS=1` and upload a large PDF | `timeout`, retried, then `max_attempts_exceeded` | TestFaultTolerance |
| Crash | Set `PARSER_JOB_MEMORY_LIMIT_MB` very low and upload a big file | `extractor_crash`; the worker itself keeps running | TestFaultTolerance, TestIsolatedParseRunner |
| Repeated crash | Same file keeps failing | Stops after `PARSER_MAX_ATTEMPTS`; listed by `?status=failed` | TestFaultTolerance |
| Storage error | Make the artifact folder read-only for a moment | Retried with backoff; a permanent error is not retried | TestFaultTolerance |
| Restart mid-job | Upload a large file, stop the worker with `Ctrl+C` or kill it, start it again | The job is picked up again and finishes | TestFaultTolerance |
| Too many jobs | Set `PARSER_QUEUE_CAPACITY=2`, stop the worker, upload three files | Third upload gets `429` with `Retry-After` | Queue tests |
| Disk nearly full | Set `PARSER_MIN_FREE_DISK_BYTES` above the free space | Uploads get `503 disk_full`; `/health/ready` says why | TestFaultTolerance |
| Many users at once | Send uploads from two Postman tabs at the same time | Both run in parallel (worker log), nobody waits | TestWorkerPool |

Restore every setting you changed after the demo.
