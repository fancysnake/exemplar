# Standards

The standards live in `standards/` in this repository, one directory per
category and one per variant inside it. A repository picks one or more variants
of each category in its `exemplar.toml`, each under its own root directory;
[Checking a repository](checking.md) covers the check itself.

Each variant gets a table whose `root` is a directory or a list of them; a
table without `root` checks the repository root. This `exemplar.toml` checks
Python at the root and Node in `frontend/`:

```toml
[lang.python]

[lang.node]
root = "frontend"
```

When every variant sits at the root, a string or a list does instead:
`lang = "python"` or `lang = ["python", "node"]`.

Fragments hold only what the maintained repositories already agree on. They
leave out tool and runtime versions: Renovate bumps those in each repository,
and a repository chooses its own minimum Python.

## Adding a standard

A standard is files in `standards/`; no code changes. A pull request here is
checked against its own branch's standards, so it may add a variant and pick
it in `exemplar.toml` at once.

A **category** is a directory, `standards/<category>/`. Every repository must
pick a variant of it, so a new category opens an item in every repository
until each one picks. To let a repository pick `none` instead, add
`standards/<category>/category.toml`:

```toml
optional = true
```

A **variant** is a directory in the category,
`standards/<category>/<variant>/`, under any name but `none`. Bits in `standards/<category>/_shared/`
belong to every variant of the category.

A **bit** is a file in the variant, at the path it has in the repository:

- A file is a whole-file bit. The repository's file must equal it.
- A directory named after a TOML, YAML or JSON file holds fragments of that
  file, one per file, each in the same format. The repository's file must
  contain each fragment: every key with an equal value, and every array item
  in any order. The repository's file may hold more.

So `standards/lang/python/pyproject.toml/project.toml` is a fragment that a
repository's `pyproject.toml` must contain, and
`standards/ci/github/.github/workflows/exemplar.yml` is a whole file.

Then give the category or variant its section on this page, with each bit
included from `standards/` as the sections below do.

## ci

Required. The workflow that runs the check.

### github

`.github/workflows/exemplar.yml` must equal:

```yaml
--8<-- "standards/ci/github/.github/workflows/exemplar.yml"
```

`renovate.json` must contain:

```json
--8<-- "standards/ci/github/renovate.json/exemplar.json"
```

The workflow names exemplar at `@main`, so every repository runs the current
check. Renovate would pin that reference to a commit, and the file would then
differ from the standard, so the rule turns Renovate off for exemplar. Every
repository on this variant holds the rule, on Renovate or not.

## lang

Required. The language the repository is written in.

### python

`pyproject.toml` must contain:

```toml
--8<-- "standards/lang/python/pyproject.toml/project.toml"
```

`mise.toml` must contain:

```toml
--8<-- "standards/lang/python/mise.toml/venv.toml"
```

### node

`package.json` must contain:

```json
--8<-- "standards/lang/node/package.json/module.json"
```
