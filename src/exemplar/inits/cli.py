"""Console-script entry point: build the CLI gate and run it."""

from __future__ import annotations

from importlib.metadata import version

from exemplar.gates.cli.typer import CliGate


def run() -> None:
    """Hand the installed version to the command line and run it."""
    CliGate(version=version("exemplar")).run()
