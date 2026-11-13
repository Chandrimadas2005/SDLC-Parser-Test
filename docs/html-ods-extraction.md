# HTML, ODS and the optional summary

## Schema 1.2 (schema-only change)

Additive and optional, so 1.1 consumers keep working:

| Field | On | Meaning |
|---|---|---|
| `href` | `link` elements | The link target as written; never followed |
| `source` | `image` elements | The image reference as written; never fetched |
| `width`, `height` | `image` elements | Declared size in whole pixels |

The schema rejects these fields on any other element kind. Golden files moved from
`"1.1"` to `"1.2"`.

## HTML (`Extraction/Html`, schema 1.2)

- BeautifulSoup over the lxml HTML parser; malformed markup is repaired as browsers do.
  Nothing is fetched, loaded or run.
- Reading order: headings (level), paragraphs, list items, tables, images, links. Text
  outside `<p>` (such as in `<div>` or `<span>`) is kept.
- Links carry `href`; images carry `source`, `width`, `height`. Inline `data:` images and
  script URLs are left out of `source`; sizes like `50%` are left out.
- Tables: own rows only, `colspan`/`rowspan` expanded, a first row of `<th>` is the header.
- Scripts, frames, objects, embeds, media and `javascript:` links are skipped, each with an
  `element_skipped` warning located at its paragraph. Result stays `succeeded`.
- `<title>`, author/description/keywords meta and `<html lang>` become file facts.
- The tree walk is iterative, so deep nesting cannot crash it.
- Locators: paragraph number and character offsets into the extracted text (schema v1 has
  no DOM path).

## ODS (`Extraction/Ods`, schema 1.1)

- Native reader: `content.xml` is streamed row by row with defusedxml, so memory stays flat
  and no extra dependency is needed.
- Sheets go through the shared `SpreadsheetTableBuilder`, so ODS gets the same header
  detection, `column_profiles`, `hidden` outline flag and formula cells
  (`formula` + `calculated_value`, the value cached at save time; nothing is recalculated)
  as XLSX.
- Real row numbers; long runs of empty repeated rows/columns cost nothing; repeat counts
  are capped at the ODF sheet size; merged cells are expanded.
- `meta.xml` title, creator, subject, description, keywords, language, dates and generator
  become file properties.
- Failures (brief 2.5):
  - archive limits checked first (`ZipArchiveGuard`) → `limit_exceeded`;
  - encryption in the manifest → `password_protected`;
  - a stream that breaks part-way keeps the sheets read so far → `partial` with
    `sheet_unreadable` for the broken sheet (still listed in the outline);
  - nothing readable → `corrupted_file`; with LibreOffice installed the file is then
    converted and parsed as XLSX, and the result carries `file_repaired` and is `partial`.
- A truncated package is still recognised as ODS from its leading `mimetype` entry.

## Optional summary

- Off by default; behind the `SummaryGenerator` port; `ExtractiveSummaryGenerator` builds
  it from the parse result only (type, counts, outline, opening text, warnings), so it
  works for every format and calls no outside service.
- Made only on request (`parser-cli ... --summary`) and only after the result is out, so it
  can never fail the parse; a failure adds `summary_unavailable` to a saved result.

## Open points

- **Shared archive-check class:** `ZipArchiveGuard` is a format-neutral stand-in until the
  shared archive-check class is on the default branch; swapping it is a one-line change
  in `ExtractorRegistry._ods`.
- **Summary API endpoint:** the worker and API do not produce or serve summaries yet
  (needs an artifact key and an endpoint).
- **Detection warnings in the shared spreadsheet path:** `SpreadsheetTableBuilder` and the
  XLSX/CSV extractors drop `extension_mismatch`; ODS adds it back itself.
- **Password input:** encrypted ODS is reported, not decrypted (no `--password` yet).
