import errno
import os
from pathlib import Path, PurePosixPath

import pytest

from exemplar.links.repo.filesystem import FilesystemRepoRepository
from exemplar.pacts import RepoError


def test_reads_file_keeping_line_endings(tmp_path):
    (tmp_path / "frontend").mkdir()
    (tmp_path / "frontend/package.json").write_bytes(b"{}\r\n")

    text = FilesystemRepoRepository(tmp_path).read(
        PurePosixPath("frontend/package.json")
    )

    assert text == "{}\r\n"


@pytest.mark.parametrize(
    "path", ["exemplar.toml", "frontend/package.json"], ids=["file", "parent"]
)
def test_missing_file_is_none(tmp_path, path):
    assert FilesystemRepoRepository(tmp_path).read(PurePosixPath(path)) is None


def test_parent_is_a_file_is_none(tmp_path):
    (tmp_path / "frontend").write_text("", encoding="utf-8")

    text = FilesystemRepoRepository(tmp_path).read(
        PurePosixPath("frontend/package.json")
    )

    assert text is None


def test_non_utf8_file_fails(tmp_path):
    (tmp_path / "exemplar.toml").write_bytes(b"\xff")

    with pytest.raises(RepoError, match=r"^not UTF-8 text$"):
        FilesystemRepoRepository(tmp_path).read(PurePosixPath("exemplar.toml"))


def test_directory_fails(tmp_path):
    (tmp_path / "exemplar.toml").mkdir()

    with pytest.raises(RepoError, match=r"^Is a directory$"):
        FilesystemRepoRepository(tmp_path).read(PurePosixPath("exemplar.toml"))


def test_unreadable_file_fails(tmp_path, monkeypatch):
    def denied(path, *_args, **_kwargs):
        raise PermissionError(errno.EACCES, os.strerror(errno.EACCES), str(path))

    # Root ignores mode bits, so chmod cannot deny access; Path is patched instead.
    monkeypatch.setattr(Path, "read_text", denied)

    with pytest.raises(RepoError, match=r"^Permission denied$"):
        FilesystemRepoRepository(tmp_path).read(PurePosixPath("exemplar.toml"))
