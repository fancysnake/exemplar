# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

exemplar checks a repository against the standards kept here
(category → variant → bits) and keeps a checklist issue in that repository.
`docs/` is the manual, built by mkdocs-material into
<https://exemplar.fancysnake.dev> by `.github/workflows/site.yml` on every
push to `main`; README.md is the front door. A new page needs a `nav` entry in
`mkdocs.yml`, and `strict: true` there makes a broken internal link fail both
`site:build` and `site:dev`.

## Commands

Python 3.11 - 3.14 via mise; never call python tools directly, always `mise run`.
The local interpreter, mypy and pylint are pinned to the 3.11 floor; CI's test
matrix covers the rest. Task definitions come from the shared
`fancysnake/shared-configs` include in `mise.toml`; `mise tasks info <task>`
shows what one runs.

```bash
mise run fullcheck     # the commit gate: format, lint, deptry, hk, tests + diff coverage
mise run test:unit     # tests/unit (mills, pure helpers)
mise run test:int      # tests/integration (links, gates)
mise run lint:py       # every linter; lint:mypy, lint:ruff, ... one at a time
mise run lint:tingle   # advisory: suppression debt vs main; not in fullcheck
mise run site:build    # the docs site; site:dev serves it with live reload
vekna rituals list     # cabinet's PR and issue rituals, configured in .vekna.toml
```

## Strictness

mypy runs fully strict including `disallow_any_expr`/`disallow_any_explicit`.
ruff selects `ALL`. tingle counts every `noqa`, `type: ignore`, `pragma`,
`cast`, `Any`, `object` use and `TODO` as debt against main. Fix the code
rather than suppress; a new suppression needs a comment saying why.

## Architecture

GLIMPSE layers, enforced by import-linter contracts in `pyproject.toml`; see
`docs/architecture.md`. Load the `glimpse` skill before adding or moving
modules.

## Config that is code

- `CHANGELOG.md` is Keep a Changelog; user-visible changes go under
  `Unreleased`.
- `pyproject.toml` carries the only version.
