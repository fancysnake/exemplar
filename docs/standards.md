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
