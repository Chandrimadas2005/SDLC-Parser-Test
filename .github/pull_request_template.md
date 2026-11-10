## Branch

`<type>/<scope>-<topic>` based on `main`

## What changed and why

<!-- Two or three lines. -->

## Commits

```
<!-- output of: git log --oneline main..HEAD -->
```

## How it was tested

<!-- Tests added, corpus files used, what you ran by hand. -->

## Results

<!-- Extractors: counts and timings on the corpus. Fault tolerance: which table row it covers. -->

## Open points

<!-- Anything you are unsure about. -->

## Checklist

- [ ] One logical unit of work, small enough to review properly
- [ ] CI is green and every commit leaves lint and tests passing
- [ ] Tests cover the change, including broken input where it applies
- [ ] Code rules met: file names, method length, parameters, complexity, typing, no literal keys
- [ ] Layer rules respected: Domain has no outside imports
- [ ] No document content in logs, no secrets, no real data
- [ ] New dependencies have an allowed licence and an entry in `docs/dependencies.md`
- [ ] Output format changes update the JSON Schema and its tests
- [ ] Schema changes come with a migration and a test
