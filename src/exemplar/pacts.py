"""GLIMPSE pacts: DTOs, protocols, errors. Depends on nothing."""

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Protocol

import msgspec
import yaml

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import PurePosixPath


class StandardsError(Exception):
    """The standards tree breaks the layout the engine reads."""


type Format = Literal["toml", "yaml", "json"]

# Parsed TOML, YAML or JSON. msgspec cannot decode into a recursive alias (its
# type analysis overflows), so values are `object`, narrowed where read.
type Parsed = object
type Table = dict[str, Parsed]


# `text` parsed as `format_`; `msgspec.DecodeError` unless it is a table.
def decode(text: str, format_: Format) -> Table:
    match format_:
        case "toml":
            return msgspec.toml.decode(text, type=dict[str, Parsed])
        case "yaml":
            return msgspec.convert(_load_yaml(text), type=dict[str, Parsed])
        case "json":
            return msgspec.json.decode(text, type=dict[str, Parsed])


# What `yaml.load` does, written out: ruff cannot tell `_YamlLoader` is safe.
def _load_yaml(text: str) -> Parsed:
    loader = _YamlLoader(text)
    try:
        document: Parsed = loader.get_single_data()
    except yaml.YAMLError as error:
        raise msgspec.DecodeError(str(error)) from error
    finally:
        loader.dispose()
    return document


_YAML_BOOL = "tag:yaml.org,2002:bool"
_YAML_12_BOOL = re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$")
# Keyed by a scalar's first character, `None` for resolvers that take any.
type _Resolvers = dict[str | None, list[tuple[str, re.Pattern[str]]]]
_YAML_11_RESOLVERS: _Resolvers = yaml.SafeLoader.yaml_implicit_resolvers
_YAML_12_RESOLVERS: _Resolvers = {
    first: [
        (tag, _YAML_12_BOOL if tag == _YAML_BOOL else regexp)
        for tag, regexp in resolvers
    ]
    for first, resolvers in _YAML_11_RESOLVERS.items()
}


class _YamlLoader(yaml.SafeLoader):
    """`SafeLoader` reading only `true` and `false` as booleans, as YAML 1.2 does.

    YAML 1.1 also reads `on`, `off`, `yes` and `no` so, turning a GitHub
    workflow's `on:` key into `True`.
    """

    yaml_implicit_resolvers = _YAML_12_RESOLVERS


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
    format: Format
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
    """A file in the checked repository exists but cannot be read as text.

    The message is the reason alone; the caller knows which file it read.
    """


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
