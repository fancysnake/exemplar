"""The checked repository's files, read from a directory on disk."""

from typing import TYPE_CHECKING

from exemplar.links.files import read_text
from exemplar.pacts import RepoError, RepoRepositoryProtocol

if TYPE_CHECKING:
    from pathlib import Path, PurePosixPath


class FilesystemRepoRepository(RepoRepositoryProtocol):
    def __init__(self, root: Path) -> None:
        self._root = root

    def read(self, path: PurePosixPath) -> str | None:
        return read_text(self._root / path, RepoError)
