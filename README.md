# exemplar

Documentation is at [exemplar.fancysnake.dev](https://exemplar.fancysnake.dev).

<!-- --8<-- [start:intro] -->
exemplar keeps a set of repositories on one set of standards. The standards
live here; each repository picks variants and nothing else.

- A **category** is one part of a project's setup: language, framework, docs,
  lint, CI. Every repository fills every category, or picks `none` where the
  category allows it.
- A **variant** is one way to fill a category: docs through `pyproject.toml`
  or through `mise.toml`. A repository may pick several, each under its own
  root directory.
- A **bit** is one file in a variant. A whole file must match exactly; a
  fragment must be contained in the repository's file of the same name.

Each repository runs exemplar in its own CI. The run keeps one issue in that
repository up to date with a checklist of every bit, and fails while any item
is open.
<!-- --8<-- [end:intro] -->

## Development

```bash
mise run fullcheck     # the commit gate
mise run site:dev      # the documentation site, with live reload
```
