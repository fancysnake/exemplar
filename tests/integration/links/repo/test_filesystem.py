import datetime
import errno
import math
import os
from pathlib import Path, PurePosixPath

import msgspec
import pytest
import yaml

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


# One table written in each format, so each reads back the same.
TABLE = {"tool": {"ruff": {"line-length": 88, "fix": True, "select": ["E", "F"]}}}


def dump(data, suffix):
    match suffix:
        case "toml" | "json":
            return getattr(msgspec, suffix).encode(data).decode()
        case _:
            return yaml.safe_dump(data)


def read_table(root, name, content):
    (root / name).write_text(content, encoding="utf-8")
    return FilesystemRepoRepository(root).read_table(PurePosixPath(name))


@pytest.mark.parametrize("suffix", ["toml", "yaml", "yml", "json"])
def test_reads_table_in_its_suffix_format(tmp_path, suffix):
    table = read_table(tmp_path, f"pyproject.{suffix}", dump(TABLE, suffix))

    assert table == TABLE


def test_missing_table_is_none(tmp_path):
    assert (
        FilesystemRepoRepository(tmp_path).read_table(PurePosixPath("a.toml")) is None
    )


@pytest.mark.parametrize(
    ("name", "content", "reason"),
    [
        ("pyproject.toml", "[", "not valid toml: "),
        ("ci.yml", "[", "not valid yaml: "),
        ("ci.yml", "- a\n", "not valid yaml: "),
        ("package.json", "[]", "not valid json: "),
    ],
    ids=["toml", "yaml", "yaml-not-a-table", "json-not-a-table"],
)
def test_unparseable_table_fails(tmp_path, name, content, reason):
    with pytest.raises(RepoError, match=rf"^{reason}"):
        read_table(tmp_path, name, content)


def test_yaml_reads_only_true_and_false_as_booleans(tmp_path):
    table = read_table(tmp_path, "ci.yml", "on: push\nstrict: true\ncolor: yes\n")

    assert table == {"on": "push", "strict": True, "color": "yes"}


@pytest.mark.parametrize(
    ("scalar", "value"),
    [
        ("0755", 755),
        ("0o14", 12),
        ("0x1F", 31),
        ("-12", -12),
        ("1e3", 1000.0),
        ("-.5", -0.5),
        (".inf", math.inf),
        ("Null", None),
        ("", None),
        ("12:30", "12:30"),
        ("1_000", "1_000"),
        ("0b11", "0b11"),
        ("2026-01-01", "2026-01-01"),
        ("=", "="),
        ("!!timestamp 2026-01-01", datetime.date(2026, 1, 1)),
    ],
)
def test_yaml_reads_scalars_by_the_yaml_12_core_schema(tmp_path, scalar, value):
    parsed = read_table(tmp_path, "ci.yml", f"key: {scalar}\n")["key"]

    assert (parsed, type(parsed)) == (value, type(value))


def test_yaml_merges_mapping_under_merge_key(tmp_path):
    table = read_table(tmp_path, "ci.yml", "base: &base {a: 1}\nmerged:\n  <<: *base\n")

    assert table["merged"] == {"a": 1}


def test_yaml_keeps_non_string_keys_at_every_depth(tmp_path):
    table = read_table(tmp_path, "codes.yaml", "200: ok\ncodes:\n  404: missing\n")

    assert table == {200: "ok", "codes": {404: "missing"}}
