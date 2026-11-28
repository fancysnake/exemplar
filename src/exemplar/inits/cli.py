"""Console-script entry point: build the CLI gate and run it."""

from __future__ import annotations

from importlib.metadata import version
from pathlib import Path

from exemplar.gates.cli.typer import CliGate
from exemplar.links.repo.filesystem import FilesystemRepoRepository
from exemplar.links.standards.filesystem import FilesystemStandardsRepository
from exemplar.mills import AuditService, BitCheckService, PicksService

# The standards tree is package data, so every install carries it.
STANDARDS = Path(__file__).parent.parent / "standards"


def audit(repo: Path, standards: Path) -> AuditService:
    files = FilesystemRepoRepository(repo)
    return AuditService(
        FilesystemStandardsRepository(standards),
        PicksService(files),
        BitCheckService(files),
    )


def run() -> None:
    """Hand the version, the audit and the shipped standards to the command line."""
    CliGate(version=version("exemplar"), audit=audit, standards=STANDARDS).run()
