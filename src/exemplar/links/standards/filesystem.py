"""The standards tree, read from `standards/<category>/<variant>/` on disk."""

from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

import msgspec

from exemplar.links.files import read_text
from exemplar.pacts import (
    NONE,
    Bit,
    Category,
    FileBit,
    FragmentBit,
    StandardsError,
    StandardsRepositoryProtocol,
    Variant,
    decode,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Mapping

    from exemplar.pacts import Format

_SHARED = "_shared"
_CATEGORY_TOML = "category.toml"
_VARIANT_ROOT = PurePosixPath()
# A directory named with one of these suffixes is a fragment directory; any
# other directory (`.github/`) holds whole-file bits. Each suffix maps to its
# format, and a fragment must share its directory's format.
_FRAGMENT_FORMATS: Mapping[str, Format] = {
    ".toml": "toml",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
}


class _CategoryToml(msgspec.Struct, forbid_unknown_fields=True, frozen=True):
    optional: bool = False


class FilesystemStandardsRepository(StandardsRepositoryProtocol):
    def __init__(self, root: Path) -> None:
        self._root = root

    def read(self) -> Mapping[str, Category]:
        if not self._root.is_dir():
            msg = f"{self._root}: not a directory"
            raise StandardsError(msg)
        return {
            entry.name: _category(entry)
            for entry in _entries(
                self._root,
                kind=Path.is_dir,
                holds="the standards root holds only category directories",
            )
        }


def _category(directory: Path) -> Category:
    bits = {
        entry.name: tuple(_bits(entry))
        for entry in _entries(
            directory,
            kind=Path.is_dir,
            holds="a category holds only variant directories",
            skip=_CATEGORY_TOML,
        )
    }
    if NONE in bits:
        msg = f"{directory / NONE}: `{NONE}` is the reserved pick, not a variant"
        raise StandardsError(msg)
    shared = bits.pop(_SHARED, ())
    return Category(
        optional=_settings(directory / _CATEGORY_TOML).optional,
        shared=shared,
        variants={name: Variant(bits=variant) for name, variant in bits.items()},
    )


def _settings(category_toml: Path) -> _CategoryToml:
    if not category_toml.exists(follow_symlinks=False):
        return _CategoryToml()
    if not category_toml.is_file():
        msg = f"{category_toml}: not a file"
        raise StandardsError(msg)
    try:
        return msgspec.toml.decode(_text(category_toml), type=_CategoryToml)
    except msgspec.DecodeError as error:
        msg = f"{category_toml}: {error}"
        raise StandardsError(msg) from error


def _bits(directory: Path, prefix: PurePosixPath = _VARIANT_ROOT) -> Iterator[Bit]:
    for entry in _entries(
        directory,
        kind=_file_or_directory,
        holds="a variant holds only files and directories",
    ):
        path = prefix / entry.name
        if entry.is_file():
            yield FileBit(path=path, content=_text(entry))
        elif entry.suffix in _FRAGMENT_FORMATS:
            yield from _fragments(entry, path)
        else:
            yield from _bits(entry, path)


def _fragments(directory: Path, path: PurePosixPath) -> Iterator[FragmentBit]:
    entries = tuple(
        _entries(
            directory,
            kind=Path.is_file,
            holds="a fragment directory holds only fragment files",
        )
    )
    if not entries:
        msg = f"{directory}: a fragment directory holds at least one fragment file"
        raise StandardsError(msg)
    format_ = _FRAGMENT_FORMATS[directory.suffix]
    for entry in entries:
        if _FRAGMENT_FORMATS.get(entry.suffix) != format_:
            msg = f"{entry}: not the format of {directory.name}"
            raise StandardsError(msg)
        try:
            content = decode(_text(entry), format_)
        except msgspec.DecodeError as error:
            msg = f"{entry}: not valid {format_}: {error}"
            raise StandardsError(msg) from error
        yield FragmentBit(
            path=path, fragment=entry.name, format=format_, content=content
        )


def _entries(
    directory: Path,
    *,
    kind: Callable[[Path], bool],
    holds: str,
    skip: str | None = None,
) -> Iterator[Path]:
    try:
        entries = sorted(directory.iterdir())
    except OSError as error:
        msg = f"{directory}: {error.strerror}"
        raise StandardsError(msg) from error
    for entry in entries:
        if entry.name == skip:
            continue
        if not kind(entry):
            msg = f"{entry}: {holds}"
            raise StandardsError(msg)
        yield entry


def _file_or_directory(entry: Path) -> bool:
    return entry.is_file() or entry.is_dir()


def _text(file: Path) -> str:
    # Every file read here was just listed, so only a race leaves it missing.
    text = read_text(file, lambda reason: StandardsError(f"{file}: {reason}"))
    if text is None:
        msg = f"{file}: missing"
        raise StandardsError(msg)
    return text
