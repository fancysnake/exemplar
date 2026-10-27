"""The checked repository's files, read from a directory on disk."""

from typing import TYPE_CHECKING

import msgspec

from exemplar.links.files import read_text
from exemplar.links.formats import FORMATS, decode
from exemplar.pacts import RepoError, RepoRepositoryProtocol

if TYPE_CHECKING:
    from pathlib import Path, PurePosixPath

    from exemplar.pacts import Table


class FilesystemRepoRepository(RepoRepositoryProtocol):
    def __init__(self, root: Path) -> None:
        self._root = root

    def read(self, path: PurePosixPath) -> str | None:
        return read_text(self._root / path, RepoError)

    def read_table(self, path: PurePosixPath) -> Table | None:
        if (text := self.read(path)) is None:
            return None
        # Only fragment bits ask for a table, and their paths end in a format.
        format_ = FORMATS[path.suffix]
        try:
            return decode(text, format_)
        except msgspec.DecodeError as error:
            msg = f"not valid {format_}: {error}"
            raise RepoError(msg) from error
