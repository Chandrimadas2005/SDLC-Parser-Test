# Test corpus

Synthetic files used by extractor, end-to-end and fault-injection tests.

**Never commit real data.** Every file here is generated or hand-written for testing and
contains no customer, employee or candidate information.

## Layout

One folder per format, each owner working in their own subfolder:

```
corpus/
  <format>/          e.g. xlsx, csv, pdf, docx, txt
    normal/          typical files
    large/           files that exercise streaming and size limits
    empty/           zero-byte or content-free files
    corrupted/       truncated or damaged files
    invalid/         malformed JSON, YAML or XML syntax
    deeply-nested/   structured input beyond depth limits
    password/        password-protected files
    wrong-extension/ real type differs from the extension
    scanned/         image-only pages that need OCR
```

Large files that are too big to commit are produced by a generator script instead, and the
script is committed.

The JSON, YAML and XML fixtures each include normal, empty, invalid, deeply nested and wrong-extension cases. All values are synthetic.
