# JSON, YAML and XML extraction

How a JSON, YAML or XML file becomes a `ParsedDocument`. All three formats share one
builder, so their output has the same shape.

## Detection

The type comes from the content; the extension is only a hint (brief, 2.1).

- JSON and XML with an `<?xml ...?>` declaration are recognised by libmagic.
- XML without a declaration is recognised when the file starts with an element and parses
  as XML. Text that only looks like a tag (`<b>bold</i> ...`) stays plain text.
- YAML is recognised from `key:` or `- item` lines.

When content and extension disagree, the content wins and the result carries an
`extension_mismatch` warning.

## Mapping to elements

| Input | Output |
|---|---|
| Top-level key | `heading`, level 1, also listed in the `outline` |
| Scalar value | `paragraph` with the value's path and value, e.g. `metadata.count: 2` |
| Nested object | One paragraph per value, path joined with `.` |
| List of scalars or mixed values | One paragraph per item, path with an index, e.g. `tags[0]: one` |
| List of objects that all have the same keys | `table`: the keys are the header row (row 1, confidence 1.0); each object is a row from row 2 |
| A file whose root is not an object (e.g. `[1, 2]`) | Everything sits under one heading named `root` |
| XML root element | Its content is the top level; a root holding only text becomes one heading named after the root |
| XML attribute | A field named `@name`, e.g. `item.@id: REQ-1` |
| XML text mixed with child elements | A field named `#text`, e.g. `note.#text: before after` |
| XML element repeated under one parent | A list, so repeated records with the same children become a table |

`true`/`false` are written in lower case and a missing value as `null`. The `words` metric
counts the words in all element text.

## Locators

Every element has a text locator: `char_start` and `char_end` are offsets into the decoded
file. `paragraph` is the element's position in reading order (1, 2, 3, ...), not a
paragraph of the source file.

- A heading points at its key.
- A paragraph points at its value. Each value is searched for after its own key and after
  the value before it, so a value that appears several times points at its own occurrence.
- A table spans from its key to the last cell of its last row.

## Results and failures

| Input | Status | Reason |
|---|---|---|
| Valid file | `succeeded` | |
| Empty or whitespace-only file (also YAML with only comments) | `succeeded`, no elements | Same as every other empty format |
| Invalid syntax, non-standard JSON constants (`NaN`, `Infinity`) | `failed` | `corrupted_file` |
| Unsafe YAML tags (`!!python/object` ...) | `failed` | `corrupted_file` (PyYAML `safe_load` never builds objects) |
| XML with DTD entities or external references (billion laughs, XXE) | `failed` | `limit_exceeded` (defusedxml) |
| Deeper than `PARSER_STRUCTURED_MAX_DEPTH` (default 32) | `failed` | `limit_exceeded` |
| More values than `PARSER_STRUCTURED_MAX_NODES` (default 100,000), counting expanded YAML aliases | `failed` | `limit_exceeded` |
| Recursive YAML alias (`a: &a [*a]`) | `failed` | `limit_exceeded` |

Both limits are settings (see [`api.md`](api.md#operational-limits)); the isolated worker
inherits them from the service environment.

## Known limitations

- A file is either parsed whole or fails whole. There is no repair step that returns the
  readable part of a broken file as `partial`.
- The file is read into memory whole (not streamed). `PARSER_MAX_FILE_SIZE_BYTES` and the
  worker memory limit bound this.
- XML namespaces appear in Clark notation, e.g. `{http://example.com/ns}item`.
