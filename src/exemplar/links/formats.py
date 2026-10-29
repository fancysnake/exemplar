"""TOML, YAML and JSON tables, parsed from text for every link that reads one."""

import re
from typing import TYPE_CHECKING, Literal

import msgspec
import yaml

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


# Plain scalars the YAML 1.2 core schema types, with the first characters each
# can start with; every other plain scalar is a string. Compose and other YAML
# 1.2 readers still merge `<<` keys, though the core schema dropped them.
_CORE_SCHEMA: list[tuple[str, str, tuple[str, ...]]] = [
    ("tag:yaml.org,2002:null", r"null|Null|NULL|~|", ("", *"nN~")),
    ("tag:yaml.org,2002:bool", r"true|True|TRUE|false|False|FALSE", tuple("tTfF")),
    (
        "tag:yaml.org,2002:int",
        r"[-+]?[0-9]+|0o[0-7]+|0x[0-9a-fA-F]+",
        tuple("-+0123456789"),
    ),
    (
        "tag:yaml.org,2002:float",
        (
            r"[-+]?(?:\.[0-9]+|[0-9]+(?:\.[0-9]*)?)(?:[eE][-+]?[0-9]+)?"
            r"|[-+]?\.(?:inf|Inf|INF)|\.(?:nan|NaN|NAN)"
        ),
        tuple("-+.0123456789"),
    ),
    ("tag:yaml.org,2002:merge", r"<<", ("<",)),
]
# Keyed by a scalar's first character, `""` for the empty scalar.
type _Resolvers = dict[str, list[tuple[str, re.Pattern[str]]]]
_YAML_12_RESOLVERS: _Resolvers = {}
for _tag, _pattern, _firsts in _CORE_SCHEMA:
    for _first in _firsts:
        _YAML_12_RESOLVERS.setdefault(_first, []).append(
            (_tag, re.compile(rf"(?:{_pattern})\Z"))
        )


class _YamlLoader(yaml.SafeLoader):
    """`SafeLoader` typing plain scalars by the YAML 1.2 core schema.

    YAML 1.1 reads a GitHub workflow's `on:` key as `True`, `0755` as octal 493
    and `12:30` as 750.
    """

    yaml_implicit_resolvers = _YAML_12_RESOLVERS


_INT_BASES = {"0o": 8, "0x": 16}


def _construct_int(loader: _YamlLoader, node: yaml.ScalarNode) -> int:
    value = loader.construct_scalar(node)
    return int(value, _INT_BASES.get(value[:2], 10))


_YamlLoader.add_constructor("tag:yaml.org,2002:int", _construct_int)
