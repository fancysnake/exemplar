"""Business logic. Depends on pacts and specs only."""

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, TypeIs

import msgspec

from exemplar.pacts import (
    NONE,
    AuditServiceProtocol,
    FileBit,
    FragmentBit,
    Pick,
    Picks,
    PicksSection,
    Problem,
    RepoError,
    RepoRepositoryProtocol,
    Report,
    Result,
    Section,
    StandardsRepositoryProtocol,
)
from exemplar.specs import EXEMPLAR_TOML

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Mapping

    from exemplar.pacts import Bit, Category, Parsed, Table

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
        text = _read(self._repo.read, EXEMPLAR_TOML)
        if isinstance(text, _Unread):
            return Picks(picks=(), problems=(Problem(where="", message=text.problem),))
        try:
            toml = msgspec.toml.decode(text, type=dict[str, _Value])
        except msgspec.DecodeError as error:
            return Picks(picks=(), problems=(Problem(where="", message=str(error)),))
        results: list[Pick | Problem] = []
        picked: set[str] = set()
        for name, value in toml.items():
            if (category := standards.get(name)) is None:
                results.append(Problem(where=name, message="unknown category"))
                continue
            variants, problems = _normalise(name, value)
            results.extend(problems)
            if not variants:
                continue
            picked.add(name)
            results.extend(_check(name, category, variants))
        results.extend(
            Problem(where=name, message="not picked")
            for name in standards
            if name not in picked
        )
        return Picks(
            picks=tuple(result for result in results if isinstance(result, Pick)),
            problems=tuple(result for result in results if isinstance(result, Problem)),
        )


class BitCheckService:
    """Checks a bit under a root: the file equals or contains the standard."""

    def __init__(self, repo: RepoRepositoryProtocol) -> None:
        self._repo = repo

    def check(self, root: PurePosixPath, bit: Bit) -> str | None:
        path = root / bit.path
        match bit:
            case FileBit(content=content):
                text = _read(self._repo.read, path)
                if isinstance(text, _Unread):
                    return text.problem
                return None if text == content else "differs from the standard"
            case FragmentBit(content=fragment):
                target = _read(self._repo.read_table, path)
                if isinstance(target, _Unread):
                    return target.problem
                return _mismatch(fragment, target, "")


class AuditService(AuditServiceProtocol):
    """Checks the picks, then every bit of each valid pick under its roots."""

    def __init__(
        self,
        standards: StandardsRepositoryProtocol,
        picks: PicksService,
        bits: BitCheckService,
    ) -> None:
        self._standards = standards
        self._picks = picks
        self._bits = bits

    def audit(self) -> Report:
        standards = self._standards.read()
        picks = self._picks.read(standards)
        return Report(
            picks=PicksSection(path=EXEMPLAR_TOML, problems=picks.problems),
            sections=tuple(
                Section(
                    category=pick.category,
                    variant=pick.variant,
                    root=root,
                    results=tuple(
                        Result(bit=bit, problem=self._bits.check(root, bit))
                        for bit in _bits(standards[pick.category], pick.variant)
                    ),
                )
                for pick in picks.picks
                for root in pick.roots
            ),
        )


def _bits(category: Category, variant: str) -> tuple[Bit, ...]:
    return (*category.variants[variant].bits, *category.shared)


# The first key path where the target does not hold the fragment, or `None`.
# Tables match key by key, extra keys allowed; every item of a fragment array
# must match some item of the target array, in any order; scalars must be
# equal and of one type, so `true` is not `1`.
def _mismatch(fragment: Parsed, target: Parsed, key: str) -> str | None:
    if _is_table(fragment):
        if not _is_table(target):
            return f"{key}: expected a table, got {_show(target)}"
        return _table_mismatch(fragment, target, key)
    if _is_array(fragment):
        if not _is_array(target):
            return f"{key}: expected an array, got {_show(target)}"
        return _array_mismatch(fragment, target, key)
    if type(fragment) is type(target) and fragment == target:
        return None
    return f"{key}: expected {_show(fragment)}, got {_show(target)}"


def _table_mismatch(table: Table, target: Table, key: str) -> str | None:
    for name, value in table.items():
        at = f"{key}.{name}" if key else f"{name}"
        if name not in target:
            return f"{at}: missing"
        if (mismatch := _mismatch(value, target[name], at)) is not None:
            return mismatch
    return None


def _array_mismatch(items: list[Parsed], target: list[Parsed], key: str) -> str | None:
    for item in items:
        if all(_mismatch(item, other, key) is not None for other in target):
            return f"{key}: missing {_show(item)}"
    return None


def _is_table(value: Parsed) -> TypeIs[Table]:
    return isinstance(value, dict)


def _is_array(value: Parsed) -> TypeIs[list[Parsed]]:
    return isinstance(value, list)


def _show(value: Parsed) -> str:
    return msgspec.json.encode(value).decode()


@dataclass(frozen=True, slots=True)
class _Unread:
    problem: str


def _read[T](
    read: Callable[[PurePosixPath], T | None], path: PurePosixPath
) -> T | _Unread:
    try:
        content = read(path)
    except RepoError as error:
        return _Unread(f"unreadable: {error}")
    if content is None:
        return _Unread("missing")
    return content


def _normalise(name: str, value: _Value) -> tuple[dict[str, list[str]], list[Problem]]:
    variants: dict[str, list[str]] = {}
    problems: list[Problem] = []
    if isinstance(value, dict):
        # `[docs.none]` defaults to `root = "."`, which cannot be told from an
        # explicit one, so the table form is refused rather than its roots.
        if NONE in value:
            problems.append(Problem(where=name, message=f"`{NONE}` cannot be a table"))
        variants = {variant: _listed(table.root) for variant, table in value.items()}
        return variants, problems
    for variant in _listed(value):
        if variant in variants:
            problems.append(Problem(where=name, message=f"`{variant}` picked twice"))
        variants[variant] = [_REPO_ROOT]
    return variants, problems


def _listed(value: str | list[str]) -> list[str]:
    return [value] if isinstance(value, str) else value


def _check(
    name: str, category: Category, variants: dict[str, list[str]]
) -> Iterator[Pick | Problem]:
    if NONE in variants:
        if len(variants) > 1:
            yield Problem(where=name, message=f"`{NONE}` mixed with other picks")
        elif not category.optional:
            yield Problem(where=name, message=f"required, cannot pick `{NONE}`")
        return
    for variant, roots in variants.items():
        if variant in category.variants:
            yield from _pick(name, variant, roots)
        else:
            yield Problem(where=name, message=f"unknown variant `{variant}`")


def _pick(name: str, variant: str, roots: list[str]) -> Iterator[Pick | Problem]:
    where = f"{name}.{variant}"
    if not roots:
        yield Problem(where=where, message="no root")
        return
    # A list, not a set: the pick keeps the roots in the order written.
    paths: list[PurePosixPath] = []
    for root in roots:
        path = PurePosixPath(root)
        if not _inside(path):
            yield Problem(
                where=where, message=f"root `{root}` is not inside the repository"
            )
        elif path in paths:
            yield Problem(where=where, message=f"root `{root}` listed twice")
        else:
            paths.append(path)
    if len(paths) == len(roots):
        yield Pick(category=name, variant=variant, roots=tuple(paths))


def _inside(root: PurePosixPath) -> bool:
    return not root.is_absolute() and ".." not in root.parts
