"""Command-line gate for exemplar (typer adapter)."""

from typing import Annotated

import typer


class CliGate:
    """The `exemplar` command line, handed what it shows by inits."""

    def __init__(self, version: str) -> None:
        self.app = typer.Typer(
            help="Check a repository against the shared standards.",
            no_args_is_help=True,
            add_completion=False,
        )

        def print_version(*, value: bool) -> None:
            if value:
                typer.echo(version)
                raise typer.Exit

        # Closures, so the eager callback reaches `version`; a method named in
        # the annotation would be handed click's Context as `self`.
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

        self.app.callback()(root)

    def run(self) -> None:
        self.app(prog_name="exemplar")
