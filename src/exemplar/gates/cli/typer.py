"""Command-line gate for exemplar (typer adapter)."""

from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Annotated

import typer

from exemplar.pacts import EXEMPLAR_TOML, FileBit, FragmentBit, StandardsError

if TYPE_CHECKING:
    from collections.abc import Callable

    from exemplar.pacts import AuditServiceProtocol, Problem, Report, Result

# Builds the audit of the repository at the first path against the standards
# tree at the second.
type Audit = Callable[[Path, Path], AuditServiceProtocol]


def _root_callback(version: str) -> Callable[[], None]:
    def print_version(*, value: bool) -> None:
        if value:
            typer.echo(version)
            raise typer.Exit

    # A closure, not a method: its annotation names `print_version`, which
    # needs `version`, and a method's annotation cannot see `self`.
    def root(
        *,
        _version: Annotated[
            bool,
            typer.Option(
                "--version",
                is_eager=True,
                callback=print_version,
                help="Print the version and exit.",
            ),
        ] = False,
    ) -> None:
        """Exit through the eager `--version` before any subcommand runs."""

    return root


def _add_check(app: typer.Typer, audit: Audit) -> None:
    def check(
        repo: Annotated[
            Path,
            typer.Argument(
                exists=True, file_okay=False, help="The repository to check."
            ),
        ] = Path(),
        *,
        standards: Annotated[
            Path,
            typer.Option(
                exists=True, file_okay=False, help="The standards tree to check by."
            ),
        ],
    ) -> None:
        try:
            report = audit(repo, standards).audit()
        except StandardsError as error:
            raise typer.BadParameter(str(error), param_hint="'--standards'") from error
        typer.echo(_render(report))
        if report.problems or any(
            result.problem is not None for result in report.results
        ):
            raise typer.Exit(1)

    # Called, not used as a decorator: mypy sees a decorator's `Any` bound.
    app.command(help="Print the repository's checklist; exit 1 if any item is open.")(
        check
    )


def _render(report: Report) -> str:
    sections: list[str] = []
    if report.problems:
        sections.append(
            _section(f"{EXEMPLAR_TOML}", [_problem(item) for item in report.problems])
        )
    groups: dict[tuple[str, str, PurePosixPath], list[str]] = {}
    for result in report.results:
        key = (result.category, result.variant, result.root)
        groups.setdefault(key, []).append(_result(result))
    sections.extend(_section(_heading(*key), lines) for key, lines in groups.items())
    return "\n\n".join(sections)


def _section(heading: str, lines: list[str]) -> str:
    return "\n".join([f"### {heading}", "", *lines])


def _heading(category: str, variant: str, root: PurePosixPath) -> str:
    heading = f"{category}: {variant}"
    return heading if root == PurePosixPath() else f"{heading} ({root})"


def _problem(problem: Problem) -> str:
    location = ".".join(
        part for part in (problem.category, problem.variant) if part is not None
    )
    return (
        f"- [ ] {location}: {problem.message}"
        if location
        else f"- [ ] {problem.message}"
    )


def _result(result: Result) -> str:
    match result.bit:
        case FileBit(path=path):
            bit = f"{path}"
        case FragmentBit(path=path, fragment=fragment):
            bit = f"{path} ⊇ {fragment}"
    if result.problem is None:
        return f"- [x] {bit}"
    return f"- [ ] {bit} — {result.problem}"


class CliGate:
    """The `exemplar` command line, handed what it shows by inits."""

    def __init__(self, version: str, audit: Audit) -> None:
        self.app = typer.Typer(
            help="Check a repository against the shared standards.",
            no_args_is_help=True,
            add_completion=False,
        )
        self.app.callback()(_root_callback(version))
        _add_check(self.app, audit)

    def run(self) -> None:
        self.app(prog_name="exemplar")
