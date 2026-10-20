"""Command-line gate for exemplar (typer adapter)."""

from __future__ import annotations

from typing import Annotated

import typer


class CliGate:
    """The `exemplar` command line, handed what it shows by inits."""

    def __init__(self, version: str) -> None:
        self._version = version
        self.app = typer.Typer(
            help="Check a repository against the shared standards.",
            no_args_is_help=True,
            add_completion=False,
        )
        self.app.callback(invoke_without_command=True)(self._root)

    def run(self) -> None:
        self.app(prog_name="exemplar")

    def _root(
        self,
        *,
        version: Annotated[
            bool, typer.Option("--version", help="Print the version and exit.")
        ] = False,
    ) -> None:
        if version:
            typer.echo(self._version)
            raise typer.Exit
