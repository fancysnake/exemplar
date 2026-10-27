"""Console-script entry point: build the CLI gate and run it."""

from __future__ import annotations

from importlib.metadata import version
from typing import TYPE_CHECKING

from exemplar.gates.cli.typer import CliGate
from exemplar.links.repo.filesystem import FilesystemRepoRepository
from exemplar.links.standards.filesystem import FilesystemStandardsRepository
from exemplar.mills import AuditService, BitCheckService, PicksService

if TYPE_CHECKING:
    from pathlib import Path


def audit(repo: Path, standards: Path) -> AuditService:
    files = FilesystemRepoRepository(repo)
    return AuditService(
        FilesystemStandardsRepository(standards),
        PicksService(files),
        BitCheckService(files),
    )


def run() -> None:
    """Hand the installed version and the audit to the command line and run it."""
    CliGate(version=version("exemplar"), audit=audit).run()
