"""The checked repository's files, read from a directory on disk."""

from typing import TYPE_CHECKING

from exemplar.pacts import RepoError, RepoRepositoryProtocol

if TYPE_CHECKING:
    from pathlib import Path, PurePosixPath


class FilesystemRepoRepository(RepoRepositoryProtocol):
    def __init__(self, root: Path) -> None:
        self._root = root

    def read(self, path: PurePosixPath) -> str | None:
        file = self._root / path
        try:
            return file.read_text(encoding="utf-8", newline="")
        # A parent that is a file means the path does not exist either.
        except FileNotFoundError, NotADirectoryError:
            return None
        except OSError as error:
            msg = f"{file}: {error.strerror}"
            raise RepoError(msg) from error
        except UnicodeDecodeError as error:
            msg = f"{file}: not UTF-8 text"
            raise RepoError(msg) from error
