"""Command-line gate for exemplar (typer adapter)."""

from typing import TYPE_CHECKING, Annotated

import typer

if TYPE_CHECKING:
    from collections.abc import Callable


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


class CliGate:
    """The `exemplar` command line, handed what it shows by inits."""

    def __init__(self, version: str) -> None:
        self.app = typer.Typer(
            help="Check a repository against the shared standards.",
            no_args_is_help=True,
            add_completion=False,
        )
        self.app.callback()(_root_callback(version))

    def run(self) -> None:
        self.app(prog_name="exemplar")
