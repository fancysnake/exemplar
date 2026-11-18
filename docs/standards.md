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

## docs

Optional. The documentation site, built by mkdocs-material. The variants
differ in what installs it.

Under every variant, `mkdocs.yml` must contain:

```yaml
--8<-- "standards/docs/_shared/mkdocs.yml/site.yml"
```

The palette has a light and a dark entry; each repository keeps its own
colours. `strict` belongs in the file and not on the command line, so that
serving the site fails on a broken link as building it does.

### mkdocs-pyproject

For a repository with a `pyproject.toml`, which must contain:

```toml
--8<-- "standards/docs/mkdocs-pyproject/pyproject.toml/docs.toml"
```

The repository chooses the version constraint.

### mkdocs-mise

For a repository without a `pyproject.toml`. `mise.toml` must contain:

```toml
--8<-- "standards/docs/mkdocs-mise/mise.toml/docs.toml"
```

mise installs mkdocs through `uvx` only when uv is installed, so `[tools]`
must also list `uv`. The check does not look for it: a fragment cannot require
a tool without also pinning its version.

## framework

Optional. The frameworks the repository builds on. A repository that uses
more than one picks each: `framework = ["astro", "react"]`.

### astro

`tsconfig.json` must contain:

```json
--8<-- "standards/framework/astro/tsconfig.json/paths.json"
```

`package.json` must contain:

```json
--8<-- "standards/framework/astro/package.json/scripts.json"
```

Each repository chooses the Astro preset its `tsconfig.json` extends.

### django

`pyproject.toml` must contain:

```toml
--8<-- "standards/framework/django/pyproject.toml/coverage.toml"

--8<-- "standards/framework/django/pyproject.toml/mypy.toml"
```

Coverage measures the templates, and mypy reads the models through the
django-stubs plugin. Each repository names its own settings module.

### react

`tsconfig.json` must contain:

```json
--8<-- "standards/framework/react/tsconfig.json/jsx.json"
```

Astro's presets point JSX at Astro, so a React island needs
`jsxImportSource` set back to `react`.

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

## lint

Optional. The linter the repository runs.

### ruff

`pyproject.toml` must contain:

```toml
--8<-- "standards/lint/ruff/pyproject.toml/lint.toml"
```

Every rule is on; each repository keeps its own `ignore` list. `line-length`
is pinned at ruff's default so that a repository that sets another length
fails the check.

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
`standards/<category>/<variant>/`, under any name but `none` or `_shared`.
Bits in `standards/<category>/_shared/` belong to every variant of the
category.

A **bit** is a file in the variant, at the path it has in the repository:

- A file is a whole-file bit. The repository's file must equal it.
- A directory named after a TOML, YAML or JSON file holds fragments of that
  file, one per file, each in the same format. The repository's file must
  contain each fragment. Tables match key by key, and nested tables the same
  way; the repository's tables may hold more keys. Every item of a fragment
  array must match some item of the repository's array, in any order. Scalars
  must be equal and of the same type, so `true` does not match `1`.
- One exception: in `pyproject.toml`, a string in `project.dependencies`, or
  in an array under `project.optional-dependencies` or `dependency-groups`,
  is a requirement and matches by package name. `mkdocs-material` matches
  `Mkdocs_Material[imaging] (>=9.6,<10.0)`; the version constraint is not
  checked. The fragment writes the requirement as a bare package name in its
  normalised form: lowercase, with `-` between words.

So `standards/lang/python/pyproject.toml/project.toml` is a fragment that a
repository's `pyproject.toml` must contain, and
`standards/ci/github/.github/workflows/exemplar.yml` is a whole file.

Then give the category or variant its section on this page, with each bit
included from `standards/` as the sections above do.
