# Architecture

The package under `src/exemplar` follows the
[GLIMPSE](https://glimpse.fancysnake.dev/) layers. Import-linter contracts in
`pyproject.toml` enforce which layer may import which.

| layer | holds | may import |
| --- | --- | --- |
| `pacts.py` | DTOs, protocols, errors | nothing internal |
| `specs.py` | constants only the business logic reads | pacts |
| `mills.py` | the checks and the report, no IO | pacts, specs |
| `links/` | adapters that read the standards tree and the checked repository | pacts |
| `gates/` | the `exemplar` command line | pacts |
| `inits/` | wiring: links into mills, mills into gates | everything |
| `edges/` | empty; nothing on a CLI needs it | nothing |

Tests live in `tests/unit/` (mills, pure helpers) and `tests/integration/`
(links and gates, against real files).
