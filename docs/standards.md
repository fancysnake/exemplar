# Standards

The standards live in `standards/` in this repository, one directory per
category and one per variant inside it. A repository picks one variant of each
category in its `exemplar.toml`; [Checking a repository](checking.md) covers
the check itself.

Fragments hold only what the maintained repositories already agree on. They
leave out tool and runtime versions: Renovate bumps those in each repository,
and a repository chooses its own minimum Python.

## lang

Required. The language the repository is written in.

| variant | file | requires |
| --- | --- | --- |
| `python` | `pyproject.toml` | `project.authors` and `project.readme = "README.md"` |
| `python` | `mise.toml` | a `.venv` virtualenv that mise creates |
| `node` | `package.json` | `"private": true` and `"type": "module"` |
