"""The standards tree, read from `standards/<category>/<variant>/` on disk."""

from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

import msgspec

from exemplar.pacts import (
    Bit,
    Category,
    FileBit,
    FragmentBit,
    Standards,
    StandardsError,
    StandardsRepositoryProtocol,
    Variant,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

_SHARED = "_shared"
_CATEGORY_TOML = "category.toml"
# A directory named like one of these is a fragment directory; any other
# directory (`.github/`) holds whole-file bits.
_FRAGMENT_SUFFIXES = frozenset({".toml", ".yaml", ".yml", ".json"})


class _CategoryToml(msgspec.Struct, forbid_unknown_fields=True, frozen=True):
    optional: bool = False


class FilesystemStandardsRepository(StandardsRepositoryProtocol):
    def __init__(self, root: Path) -> None:
        self._root = root

    def read(self) -> Standards:
        if not self._root.is_dir():
            msg = f"{self._root}: not a directory"
            raise StandardsError(msg)
        return Standards(
            categories={
                entry.name: _category(entry) for entry in _directories(self._root)
            }
        )


def _category(directory: Path) -> Category:
    shared: tuple[Bit, ...] = ()
    variants: dict[str, Variant] = {}
    for entry in sorted(directory.iterdir()):
        if entry.name == _CATEGORY_TOML:
            continue
        if not entry.is_dir():
            msg = f"{entry}: a category holds only variant directories"
            raise StandardsError(msg)
        bits = tuple(_bits(entry, entry))
        if entry.name == _SHARED:
            shared = bits
        else:
            variants[entry.name] = Variant(name=entry.name, bits=bits)
    return Category(
        name=directory.name,
        optional=_optional(directory / _CATEGORY_TOML),
        shared=shared,
        variants=variants,
    )


def _optional(category_toml: Path) -> bool:
    if not category_toml.is_file():
        return False
    try:
        return msgspec.toml.decode(
            category_toml.read_bytes(), type=_CategoryToml
        ).optional
    except msgspec.DecodeError as error:
        msg = f"{category_toml}: {error}"
        raise StandardsError(msg) from error


def _bits(directory: Path, variant: Path) -> Iterator[Bit]:
    for entry in sorted(directory.iterdir()):
        path = PurePosixPath(entry.relative_to(variant).as_posix())
        if entry.is_file():
            yield FileBit(path=path, content=_text(entry))
        elif entry.suffix in _FRAGMENT_SUFFIXES:
            yield from _fragments(entry, path)
        else:
            yield from _bits(entry, variant)


def _fragments(directory: Path, path: PurePosixPath) -> Iterator[FragmentBit]:
    for entry in sorted(directory.iterdir()):
        if not entry.is_file():
            msg = f"{entry}: a fragment directory holds only fragment files"
            raise StandardsError(msg)
        yield FragmentBit(path=path, fragment=entry.name, content=_text(entry))


def _directories(root: Path) -> Iterator[Path]:
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            msg = f"{entry}: the standards root holds only category directories"
            raise StandardsError(msg)
        yield entry


def _text(file: Path) -> str:
    try:
        return file.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        msg = f"{file}: not UTF-8 text"
        raise StandardsError(msg) from error
