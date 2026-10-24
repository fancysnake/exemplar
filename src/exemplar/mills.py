"""Business logic. Depends on pacts and specs only."""

from pathlib import PurePosixPath
from typing import TYPE_CHECKING

import msgspec

from exemplar.pacts import NONE, Pick, Picks, RepoError, RepoRepositoryProtocol
from exemplar.specs import EXEMPLAR_TOML

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from exemplar.pacts import Category, FileBit

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
        try:
            text = self._repo.read(EXEMPLAR_TOML)
        except RepoError as error:
            return Picks(picks=(), problems=(str(error),))
        if text is None:
            return Picks(picks=(), problems=(f"{EXEMPLAR_TOML}: missing",))
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


class FileCheckService:
    """Checks a whole-file bit: under every root, the file equals the standard."""

    def __init__(self, repo: RepoRepositoryProtocol) -> None:
        self._repo = repo

    def check(self, pick: Pick, bit: FileBit) -> tuple[str, ...]:
        return tuple(
            f"{pick.category}.{pick.variant}: {problem}"
            for root in pick.roots
            if (problem := self._problem(root / bit.path, bit.content))
        )

    def _problem(self, path: PurePosixPath, content: str) -> str | None:
        try:
            text = self._repo.read(path)
        except RepoError as error:
            return str(error)
        if text is None:
            return f"`{path}` missing"
        if text != content:
            return f"`{path}` differs from the standard"
        return None


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
