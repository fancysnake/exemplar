# Checking a repository

`exemplar check` reads the repository's picks from `exemplar.toml`, checks
every bit of every pick under each of its roots, and prints a markdown
checklist:

```bash
exemplar check path/to/repo --standards path/to/standards
```

The repository defaults to the current directory. `--standards` is the
standards tree: one directory per category, one per variant inside it.

## The checklist

Each pick gets a section per root; a root other than the repository's own is
named in brackets. A whole-file bit is listed by its path, a fragment bit as
`file ⊇ fragment`. An open item says what is wrong.

```markdown
### exemplar.toml

- [ ] docs: not picked

### lint: ruff

- [ ] pyproject.toml ⊇ ruff.toml — tool.ruff.line-length: expected 88, got 100
- [x] ruff.toml

### lang: node (frontend)

- [ ] .nvmrc — missing
```

The `exemplar.toml` section appears only when a pick is wrong: an unknown
category or variant, a category left unpicked, a root outside the repository.
A broken pick checks no bits.

## Exit codes

| code | meaning |
| --- | --- |
| 0 | every item is ticked |
| 1 | at least one item is open |
| 2 | the command line or the standards tree is wrong; nothing was checked |

## In CI

exemplar is also a GitHub Action, and it ships with its own standards tree. A
repository on `fancysnake/exemplar@main` is always checked against the current
standards.

```yaml
jobs:
  exemplar:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1  # v7
        with:
          persist-credentials: false
      - uses: fancysnake/exemplar@main
```

The action installs its own Python and leaves the job's toolchain alone, then
runs `exemplar check`. It fails while any item is open. The checklist goes to
the log and to the job summary; the `checklist` output is the path of the file
holding it.

| input | default | meaning |
| --- | --- | --- |
| `path` | `.` | the repository to check, relative to the workspace |
