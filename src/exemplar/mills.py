"""Business logic. Depends on pacts and specs only."""

from pathlib import PurePosixPath
from typing import TYPE_CHECKING

import msgspec

from exemplar.pacts import Pick, Picks, RepoRepositoryProtocol
from exemplar.specs import EXEMPLAR_TOML, NONE

if TYPE_CHECKING:
    from collections.abc import Mapping

    from exemplar.pacts import Category

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
        if (text := self._repo.read(EXEMPLAR_TOML)) is None:
            return Picks(picks=(), problems=(f"{EXEMPLAR_TOML}: missing",))
        try:
            toml = msgspec.toml.decode(text, type=dict[str, _Value])
        except msgspec.DecodeError as error:
            return Picks(picks=(), problems=(f"{EXEMPLAR_TOML}: {error}",))
        picks: list[Pick] = []
        problems: list[str] = []
        picked: set[str] = set()
        for name, value in toml.items():
            if (category := standards.get(name)) is None:
                problems.append(f"{name}: unknown category")
                continue
            if variants := _normalise(value):
                picked.add(name)
            _check(name, category, variants, picks, problems)
        problems.extend(
            f"{name}: not picked" for name in standards if name not in picked
        )
        return Picks(picks=tuple(picks), problems=tuple(problems))


def _normalise(value: _Value) -> list[tuple[str, list[str]]]:
    match value:
        case str():
            return [(value, [_REPO_ROOT])]
        case list():
            return [(variant, [_REPO_ROOT]) for variant in value]
        case _:
            return [
                (variant, [table.root] if isinstance(table.root, str) else table.root)
                for variant, table in value.items()
            ]


def _check(
    name: str,
    category: Category,
    variants: list[tuple[str, list[str]]],
    picks: list[Pick],
    problems: list[str],
) -> None:
    variants = _once(name, variants, problems)
    if any(variant == NONE for variant, _ in variants):
        if len(variants) > 1:
            problems.append(f"{name}: `{NONE}` mixed with other picks")
        elif not category.optional:
            problems.append(f"{name}: required, cannot pick `{NONE}`")
        return
    for variant, roots in variants:
        if variant not in category.variants:
            problems.append(f"{name}: unknown variant `{variant}`")
            continue
        if not roots:
            problems.append(f"{name}.{variant}: no root")
            continue
        paths = [PurePosixPath(root) for root in roots]
        bad = [
            *(
                f"{name}.{variant}: root `{root}` is not inside the repository"
                for root, path in zip(roots, paths, strict=True)
                if not _inside(path)
            ),
            *(
                f"{name}.{variant}: root `{root}` listed twice"
                for index, (root, path) in enumerate(zip(roots, paths, strict=True))
                if path in paths[:index]
            ),
        ]
        if bad:
            problems.extend(bad)
            continue
        picks.append(Pick(category=name, variant=variant, roots=tuple(paths)))


def _once(
    name: str, variants: list[tuple[str, list[str]]], problems: list[str]
) -> list[tuple[str, list[str]]]:
    once: list[tuple[str, list[str]]] = []
    seen: set[str] = set()
    for variant, roots in variants:
        if variant in seen:
            problems.append(f"{name}: `{variant}` picked twice")
            continue
        seen.add(variant)
        once.append((variant, roots))
    return once


def _inside(root: PurePosixPath) -> bool:
    return not root.is_absolute() and ".." not in root.parts
