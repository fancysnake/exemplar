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
