"""GLIMPSE pacts: DTOs, protocols, errors. Depends on nothing."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import PurePosixPath


class StandardsError(Exception):
    """The standards tree breaks the layout the engine reads."""


@dataclass(frozen=True, slots=True, kw_only=True)
class FileBit:
    """A file the target must hold with exactly this content."""

    path: PurePosixPath
    content: str


@dataclass(frozen=True, slots=True, kw_only=True)
class FragmentBit:
    """A fragment the target file at `path` must contain as a deep subset."""

    path: PurePosixPath
    fragment: str
    content: str


type Bit = FileBit | FragmentBit


@dataclass(frozen=True, slots=True, kw_only=True)
class Variant:
    bits: tuple[Bit, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class Category:
    """A category's variants, and the bits every non-`none` pick shares."""

    optional: bool
    shared: tuple[Bit, ...]
    variants: Mapping[str, Variant]


class StandardsRepositoryProtocol(Protocol):
    def read(self) -> Mapping[str, Category]: ...


class RepoError(Exception):
    """A file in the checked repository exists but cannot be read as text."""


class RepoRepositoryProtocol(Protocol):
    def read(self, path: PurePosixPath) -> str | None:
        """Return the file at `path` in the repository, or `None` if missing."""


@dataclass(frozen=True, slots=True, kw_only=True)
class Pick:
    """A variant the repository picked for a category, and where it applies."""

    category: str
    variant: str
    roots: tuple[PurePosixPath, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class Picks:
    """The valid picks, and a checklist line for each one that failed."""

    picks: tuple[Pick, ...]
    problems: tuple[str, ...]
