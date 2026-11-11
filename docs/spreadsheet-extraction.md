# Spreadsheet extraction implementation notes

## XLSX and XLSM streaming trade-off

The XLSX/XLSM extractor opens the workbook twice in `read_only=True` mode: the first
pass reads formula expressions and the second `data_only=True` pass reads the cached
calculated values written by the spreadsheet application. A cached value may be absent
when the workbook has not been recalculated and saved by a spreadsheet application; in
that case the formula is still retained and the calculated value is omitted.

Openpyxl's read-only worksheet interface does not expose merged-cell ranges. Rather
than opening a second normal-mode workbook (which would materialize worksheet cells in
memory), the extractor reads only the worksheet XML merge metadata from the XLSX ZIP
container with incremental XML parsing. It then expands merged values in the emitted
table. Worksheet values themselves remain streamed through openpyxl's read-only row
iterator. This avoids a full normal-mode workbook load, at the cost of a second pass
and a small XML metadata scan. Macros are never executed and VBA content is not loaded.

The output `ParsedDocument` necessarily retains extracted rows because its contract
returns the complete structured table; the streaming guarantee applies to workbook
loading and row ingestion, not to the final result object.
