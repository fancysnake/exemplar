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

`mise.toml` must also contain:

```toml
--8<-- "standards/docs/mkdocs-mise/mise.toml/site.toml"
```

mise keeps one install of each mkdocs version for the whole machine. When
another project installed that version without mkdocs-material, mise reuses
the install and the theme is missing. `site:material` then stops `site:build`
and `site:dev` with the command that repairs the install. Each repository
writes its own `run` for those two tasks.

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

### asyncio

`pyproject.toml` must contain:

```toml
--8<-- "standards/framework/asyncio/pyproject.toml/dev.toml"
```

The plugin lets pytest run `async def` tests. The repository chooses the version constraint.

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

### oxlint

oxlint with its formatter, oxfmt. `.oxfmtrc.json` must contain:

```json
--8<-- "standards/lint/oxlint/.oxfmtrc.json/imports.json"
```

Each repository keeps its own oxlint rules. The check finds each import group
in the array but not its position: an array matches in any order.

### ruff

`pyproject.toml` must contain:

```toml
--8<-- "standards/lint/ruff/pyproject.toml/lint.toml"
```

Every rule is on; each repository keeps its own `ignore` list. `line-length`
is pinned at ruff's default so that a repository that sets another length
fails the check.

## owner

Optional. Who owns the project. A repository with another owner, such as a
fork, picks `none`.

### radoslaw-ganczarek

`pyproject.toml` must contain:

```toml
--8<-- "standards/owner/radoslaw-ganczarek/pyproject.toml/authors.toml"
```

The repository may list more authors.

## renovate

Optional. How Renovate updates the dependencies. Each variant is one package
system; a repository picks every variant that it uses:
`renovate = ["poetry", "hk"]`.

Under every variant, `renovate.json` must contain:

```json
--8<-- "standards/renovate/_shared/renovate.json/base.json"
```

Renovate offers a release only when the release is 7 days old. `strict` makes
Renovate skip a newer release and offer the newest release that is old enough.

`renovate.json` must also contain:

```json
--8<-- "standards/renovate/_shared/renovate.json/groups.json"
```

The first rule puts every minor, patch and digest update in one pull request.
The second rule gives a minor update of a 0.x package its own pull request,
because a 0.x minor can break. Renovate applies the rules in order, so the
second rule must come after the first. The check does not look at the order.

### poetry

For a repository whose `pyproject.toml` holds the dependencies.
`renovate.json` must contain:

```json
--8<-- "standards/renovate/poetry/renovate.json/ranges.json"
```

`config:best-practices` pins development dependencies to one version. The
preset keeps a range such as `>=1.2,<2` a range.

### mise-python

For a repository whose `requires-python` allows one minor version and whose
`mise.toml` installs Python. `renovate.json` must contain:

```json
--8<-- "standards/renovate/mise-python/renovate.json/minor.json"
```

The second rule turns off the update to the next Python minor, which
`requires-python` forbids. Without the first rule, Renovate offers only the
newest version, so no patch arrives after the next minor is released.

### aube

For a repository that installs Node packages with aube. `renovate.json` must
contain:

```json
--8<-- "standards/renovate/aube/renovate.json/npm.json"
```

Renovate cannot write `aube-lock.yaml`. An npm update would change only
`package.json`, and the install from the frozen lockfile would fail. The
repository updates its Node packages with `aube update`.

### hk

For a repository with an `hk.pkl`. `renovate.json` must contain:

```json
--8<-- "standards/renovate/hk/renovate.json/pkl.json"
```

`hk.pkl` names the hk release in a package URL that no Renovate manager
reads. The custom manager updates that URL from the releases of `jdx/hk`.

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
