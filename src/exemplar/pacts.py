"""GLIMPSE pacts: DTOs, protocols, errors. Depends on nothing."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
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
    name: str
    bits: tuple[Bit, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class Category:
    """A category's variants, and the bits every non-`none` pick shares."""

    name: str
    optional: bool
    shared: tuple[Bit, ...]
    variants: dict[str, Variant]


@dataclass(frozen=True, slots=True, kw_only=True)
class Standards:
    categories: dict[str, Category]


class StandardsRepositoryProtocol(Protocol):
    def read(self) -> Standards: ...
