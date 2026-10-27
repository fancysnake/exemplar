"""GLIMPSE pacts: DTOs, protocols, errors. Depends on nothing."""

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Mapping


class StandardsError(Exception):
    """The standards tree breaks the layout the engine reads."""


# Parsed TOML, YAML or JSON. msgspec cannot decode into a recursive alias (its
# type analysis overflows), so values are `object`, narrowed where read. YAML
# keys may be any scalar, so table keys are `object` too.
type Parsed = object
type Table = dict[Parsed, Parsed]


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
    content: Table


type Bit = FileBit | FragmentBit

# What an optional category picks when the repository has nothing for it, so
# no category may hold a variant of that name.
NONE = "none"


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
    """A file in the checked repository exists but cannot be read as asked.

    The message is the reason alone; the caller knows which file it read.
    """


class RepoRepositoryProtocol(Protocol):
    def read(self, path: PurePosixPath) -> str | None:
        """Return the file at `path` in the repository, or `None` if missing."""

    def read_table(self, path: PurePosixPath) -> Table | None:
        """Return the file at `path` parsed by its suffix, or `None` if missing.

        `RepoError` also when the file is not a table in that format.
        """


# Where the repository picks its variants; the checklist names it too.
EXEMPLAR_TOML = PurePosixPath("exemplar.toml")


@dataclass(frozen=True, slots=True, kw_only=True)
class Pick:
    """A variant the repository picked for a category, and where it applies."""

    category: str
    variant: str
    roots: tuple[PurePosixPath, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class Problem:
    """What is wrong in `exemplar.toml`, and the category or pick it is under."""

    message: str
    category: str | None = None
    variant: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class Picks:
    """The valid picks, and a problem for each one that failed."""

    picks: tuple[Pick, ...]
    problems: tuple[Problem, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class Result:
    """One bit checked under one root of a pick; `problem` is `None` on a pass."""

    category: str
    variant: str
    root: PurePosixPath
    bit: Bit
    problem: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class Report:
    """Every problem with the picks, and every bit checked under them."""

    problems: tuple[Problem, ...]
    results: tuple[Result, ...]


class AuditServiceProtocol(Protocol):
    def audit(self) -> Report:
        """Check the repository's picks and every bit they pick.

        `StandardsError` when the standards tree cannot be read.
        """
