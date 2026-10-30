"""TOML, YAML and JSON tables, parsed from text for every link that reads one."""

import re
from typing import TYPE_CHECKING, Literal

import msgspec
import yaml
from yaml.constructor import ConstructorError
from yaml.error import Mark

from exemplar.pacts import Parsed

if TYPE_CHECKING:
    from collections.abc import Mapping

    from exemplar.pacts import Table

type Format = Literal["toml", "yaml", "json"]

# Each file suffix that names a format.
FORMATS: Mapping[str, Format] = {
    ".toml": "toml",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
}


# `text` parsed as `format_`; `msgspec.DecodeError` unless it is a table.
def decode(text: str, format_: Format) -> Table:
    match format_:
        case "toml":
            return msgspec.toml.decode(text, type=dict[Parsed, Parsed])
        case "yaml":
            return msgspec.convert(_load_yaml(text), type=dict[Parsed, Parsed])
        case "json":
            return msgspec.json.decode(text, type=dict[Parsed, Parsed])


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


class _YamlLoader(yaml.SafeLoader):
    """`SafeLoader` typing plain scalars by the YAML 1.2 core schema.

    YAML 1.1 reads a GitHub workflow's `on:` key as `True`, `0755` as octal 493
    and `12:30` as 750.
    """


_INT_BASES = {"0o": 8, "0x": 16}


def _construct_int(loader: _YamlLoader, node: yaml.ScalarNode) -> int:
    value = loader.construct_scalar(node)
    try:
        return int(value, _INT_BASES.get(value[:2], 10))
    except ValueError as error:
        # The stub types `start_mark` as `Mark | Any`; the pattern narrows it.
        mark = None
        match node:
            case object(start_mark=Mark() as start_mark):
                mark = start_mark
        raise ConstructorError(None, None, str(error), mark) from error


# Types the plain scalars matching `pattern` and starting with a character of
# `firsts`, `""` for the empty scalar, as `tag`.
def _resolve(tag: str, pattern: str, firsts: list[str]) -> None:
    regexp = re.compile(rf"(?:{pattern})\Z")
    _YamlLoader.add_implicit_resolver(tag, regexp, firsts)


# Its own table, so `add_implicit_resolver` skips copying YAML 1.1's. Every
# plain scalar the core schema leaves untyped is a string. Compose and other
# YAML 1.2 readers still merge `<<` keys, though the core schema dropped them.
_YamlLoader.yaml_implicit_resolvers = dict[str, list[tuple[str, re.Pattern[str]]]]()
_resolve("tag:yaml.org,2002:null", r"null|Null|NULL|~|", ["", *"nN~"])
_resolve("tag:yaml.org,2002:bool", r"true|True|TRUE|false|False|FALSE", [*"tTfF"])
_resolve(
    "tag:yaml.org,2002:int", r"[-+]?[0-9]+|0o[0-7]+|0x[0-9a-fA-F]+", [*"-+0123456789"]
)
_resolve(
    "tag:yaml.org,2002:float",
    (
        r"[-+]?(?:\.[0-9]+|[0-9]+(?:\.[0-9]*)?)(?:[eE][-+]?[0-9]+)?"
        r"|[-+]?\.(?:inf|Inf|INF)|\.(?:nan|NaN|NAN)"
    ),
    [*"-+.0123456789"],
)
_resolve("tag:yaml.org,2002:merge", r"<<", ["<"])
_YamlLoader.add_constructor("tag:yaml.org,2002:int", _construct_int)
