"""Business logic. Depends on pacts and specs only."""

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

import msgspec

from exemplar.pacts import (
    NONE,
    FileBit,
    FragmentBit,
    Pick,
    Picks,
    RepoError,
    RepoRepositoryProtocol,
    StandardsError,
)
from exemplar.specs import EXEMPLAR_TOML

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Mapping

    from exemplar.pacts import Bit, Category, Format

_REPO_ROOT = "."


class _PickTable(msgspec.Struct, forbid_unknown_fields=True, frozen=True):
    root: str | list[str] = _REPO_ROOT


# A category's value: `docs = "x"`, `lint = ["x", "y"]`, or `[lang.node]` tables.
type _Value = str | list[str] | dict[str, _PickTable]


class PicksService:
    """Reads the repository's `exemplar.toml` and checks its picks."""

    def __init__(self, repo: RepoRepositoryProtocol) -> None:
        self._repo = repo

    def read(self, standards: Mapping[str, Category]) -> Picks:
        text = _read(self._repo, EXEMPLAR_TOML)
        if isinstance(text, _Unread):
            return Picks(picks=(), problems=(text.problem,))
        try:
            toml = msgspec.toml.decode(text, type=dict[str, _Value])
        except msgspec.DecodeError as error:
            return Picks(picks=(), problems=(f"{EXEMPLAR_TOML}: {error}",))
        results: list[Pick | str] = []
        picked: set[str] = set()
        for name, value in toml.items():
            if (category := standards.get(name)) is None:
                results.append(f"{name}: unknown category")
                continue
            variants, problems = _normalise(name, value)
            results.extend(problems)
            if not variants:
                continue
            picked.add(name)
            results.extend(_check(name, category, variants))
        results.extend(
            f"{name}: not picked" for name in standards if name not in picked
        )
        return Picks(
            picks=tuple(result for result in results if isinstance(result, Pick)),
            problems=tuple(result for result in results if isinstance(result, str)),
        )


class BitCheckService:
    """Checks a bit under every root: the file equals or contains the standard."""

    def __init__(self, repo: RepoRepositoryProtocol) -> None:
        self._repo = repo

    def check(self, pick: Pick, bit: Bit) -> tuple[str, ...]:
        compare = _comparison(bit)
        return tuple(
            f"{pick.category}.{pick.variant}: {problem}"
            for root in pick.roots
            if (problem := self._problem(root / bit.path, compare))
        )

    def _problem(
        self, path: PurePosixPath, compare: Callable[[str], str | None]
    ) -> str | None:
        text = _read(self._repo, path)
        if isinstance(text, _Unread):
            return text.problem
        if (mismatch := compare(text)) is None:
            return None
        return f"`{path}` {mismatch}"


# Parsed TOML, YAML or JSON. msgspec cannot decode into a recursive alias (its
# type analysis overflows), so values are `object`, narrowed by `_as`.
type _Parsed = object


def _comparison(bit: Bit) -> Callable[[str], str | None]:
    match bit:
        case FileBit(content=content):
            return lambda text: None if text == content else "differs from the standard"
        case FragmentBit(fragment=name, format=format_, content=content):
            try:
                fragment = _decode(content, format_)
            except msgspec.DecodeError as error:
                msg = f"`{name}`: not valid {format_}: {error}"
                raise StandardsError(msg) from error
            return lambda text: _contains(text, name, format_, fragment)


def _contains(
    text: str, name: str, format_: Format, fragment: dict[str, _Parsed]
) -> str | None:
    try:
        target = _decode(text, format_)
    except msgspec.DecodeError as error:
        return f"not valid {format_}: {error}"
    if (mismatch := _mismatch(fragment, target, "")) is None:
        return None
    return f"⊇ `{name}`: {mismatch}"


def _decode(text: str, format_: Format) -> dict[str, _Parsed]:
    match format_:
        case "toml":
            return msgspec.toml.decode(text, type=dict[str, _Parsed])
        case "yaml":
            return msgspec.yaml.decode(text, type=dict[str, _Parsed])
        case "json":
            return msgspec.json.decode(text, type=dict[str, _Parsed])


# The first key path where the target does not hold the fragment, or `None`.
# Tables match key by key, extra keys allowed; every item of a fragment array
# must match some item of the target array, in any order; scalars must be
# equal and of one type, so `true` is not `1`.
def _mismatch(fragment: _Parsed, target: _Parsed, key: str) -> str | None:
    if (table := _as(fragment, dict[str, _Parsed])) is not None:
        if (target_table := _as(target, dict[str, _Parsed])) is None:
            return f"{key}: expected a table, got {_show(target)}"
        return _table_mismatch(table, target_table, key)
    if (items := _as(fragment, list[_Parsed])) is not None:
        if (target_items := _as(target, list[_Parsed])) is None:
            return f"{key}: expected an array, got {_show(target)}"
        return _array_mismatch(items, target_items, key)
    if type(fragment) is type(target) and fragment == target:
        return None
    return f"{key}: expected {_show(fragment)}, got {_show(target)}"


def _table_mismatch(
    table: dict[str, _Parsed], target: dict[str, _Parsed], key: str
) -> str | None:
    for name, value in table.items():
        at = f"{key}.{name}" if key else name
        if name not in target:
            return f"{at}: missing"
        if (mismatch := _mismatch(value, target[name], at)) is not None:
            return mismatch
    return None


def _array_mismatch(
    items: list[_Parsed], target: list[_Parsed], key: str
) -> str | None:
    for item in items:
        if all(_mismatch(item, other, key) is not None for other in target):
            return f"{key}: missing {_show(item)}"
    return None


def _as[T](value: _Parsed, kind: type[T]) -> T | None:
    try:
        return msgspec.convert(value, type=kind)
    except msgspec.ValidationError:
        return None


def _show(value: _Parsed) -> str:
    return msgspec.json.encode(value).decode()


@dataclass(frozen=True, slots=True)
class _Unread:
    problem: str


def _read(repo: RepoRepositoryProtocol, path: PurePosixPath) -> str | _Unread:
    try:
        text = repo.read(path)
    except RepoError as error:
        return _Unread(f"`{path}` unreadable: {error}")
    if text is None:
        return _Unread(f"`{path}` missing")
    return text


def _normalise(name: str, value: _Value) -> tuple[dict[str, list[str]], list[str]]:
    variants: dict[str, list[str]] = {}
    problems: list[str] = []
    if isinstance(value, dict):
        # `[docs.none]` defaults to `root = "."`, which cannot be told from an
        # explicit one, so the table form is refused rather than its roots.
        if NONE in value:
            problems.append(f"{name}: `{NONE}` cannot be a table")
        variants = {variant: _listed(table.root) for variant, table in value.items()}
        return variants, problems
    for variant in _listed(value):
        if variant in variants:
            problems.append(f"{name}: `{variant}` picked twice")
        variants[variant] = [_REPO_ROOT]
    return variants, problems


def _listed(value: str | list[str]) -> list[str]:
    return [value] if isinstance(value, str) else value


def _check(
    name: str, category: Category, variants: dict[str, list[str]]
) -> Iterator[Pick | str]:
    if NONE in variants:
        if len(variants) > 1:
            yield f"{name}: `{NONE}` mixed with other picks"
        elif not category.optional:
            yield f"{name}: required, cannot pick `{NONE}`"
        return
    for variant, roots in variants.items():
        if variant in category.variants:
            yield from _pick(name, variant, roots)
        else:
            yield f"{name}: unknown variant `{variant}`"


def _pick(name: str, variant: str, roots: list[str]) -> Iterator[Pick | str]:
    if not roots:
        yield f"{name}.{variant}: no root"
        return
    # A list, not a set: the pick keeps the roots in the order written.
    paths: list[PurePosixPath] = []
    for root in roots:
        path = PurePosixPath(root)
        if not _inside(path):
            yield f"{name}.{variant}: root `{root}` is not inside the repository"
        elif path in paths:
            yield f"{name}.{variant}: root `{root}` listed twice"
        else:
            paths.append(path)
    if len(paths) == len(roots):
        yield Pick(category=name, variant=variant, roots=tuple(paths))


def _inside(root: PurePosixPath) -> bool:
    return not root.is_absolute() and ".." not in root.parts
