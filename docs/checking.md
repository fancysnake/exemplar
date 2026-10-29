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
