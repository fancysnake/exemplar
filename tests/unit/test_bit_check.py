from pathlib import PurePosixPath
from unittest.mock import MagicMock, call

import pytest

from exemplar.mills import BitCheckService
from exemplar.pacts import FileBit, FragmentBit, Pick, RepoError

BIT = FileBit(path=PurePosixPath(".github/renovate.json"), content="{}\n")


def check(contents, *roots, bit=BIT):
    repo = MagicMock()
    read = repo.read if isinstance(bit, FileBit) else repo.read_table
    read.side_effect = contents
    pick = Pick(
        category="ci",
        variant="github",
        roots=tuple(PurePosixPath(root) for root in roots or (".",)),
    )
    problems = BitCheckService(repo).check(pick, bit)
    assert read.call_args_list == [
        call(PurePosixPath(root) / bit.path) for root in roots or (".",)
    ]
    return problems


def test_identical_file_passes():
    assert not check(["{}\n"])


@pytest.mark.parametrize(
    ("text", "problem"),
    [
        (None, "ci.github: `.github/renovate.json` missing"),
        ("{ }\n", "ci.github: `.github/renovate.json` differs from the standard"),
        ("{}\r\n", "ci.github: `.github/renovate.json` differs from the standard"),
        ("{}", "ci.github: `.github/renovate.json` differs from the standard"),
    ],
    ids=["missing", "different", "line-endings", "no-final-newline"],
)
def test_file_not_matching_fails(text, problem):
    assert check([text]) == (problem,)


def test_unreadable_file_fails():
    assert check([RepoError("not UTF-8 text")]) == (
        "ci.github: `.github/renovate.json` unreadable: not UTF-8 text",
    )


def test_each_root_is_checked():
    assert check([None, "{}\n", "{ }\n"], "frontend", "admin", "api") == (
        "ci.github: `frontend/.github/renovate.json` missing",
        "ci.github: `api/.github/renovate.json` differs from the standard",
    )


FRAGMENT = {"tool": {"ruff": {"line-length": 88, "select": ["E", "F"]}}}


def check_fragment(target, fragment=None):
    bit = FragmentBit(
        path=PurePosixPath("pyproject.toml"),
        fragment="ruff.toml",
        content=fragment or FRAGMENT,
    )
    return check([target], bit=bit)


def unmet(mismatch):
    return f"ci.github: `pyproject.toml` lacks `ruff.toml`: {mismatch}"


def test_equal_fragment_passes():
    assert not check_fragment(FRAGMENT)


def test_extra_keys_and_items_pass():
    target = {
        "project": {"name": "x"},
        "tool": {"ruff": {"line-length": 88, "select": ["I", "F", "E"], "fix": True}},
    }

    assert not check_fragment(target)


@pytest.mark.parametrize(
    ("ruff", "mismatch"),
    [
        ({"select": ["E", "F"]}, "tool.ruff.line-length: missing"),
        (
            {"line-length": 100, "select": ["E", "F"]},
            "tool.ruff.line-length: expected 88, got 100",
        ),
        (
            {"line-length": True, "select": ["E", "F"]},
            "tool.ruff.line-length: expected 88, got true",
        ),
        ({"line-length": 88, "select": ["E"]}, 'tool.ruff.select: missing "F"'),
        (
            {"line-length": 88, "select": "E"},
            'tool.ruff.select: expected an array, got "E"',
        ),
    ],
    ids=[
        "missing-key",
        "different-value",
        "bool-is-not-int",
        "missing-item",
        "not-an-array",
    ],
)
def test_first_mismatch_fails(ruff, mismatch):
    assert check_fragment({"tool": {"ruff": ruff}}) == (unmet(mismatch),)


def test_table_replaced_by_value_fails():
    assert check_fragment({"tool": {"ruff": 1}}) == (
        unmet("tool.ruff: expected a table, got 1"),
    )


def test_array_items_match_as_fragments():
    fragment = {"repos": [{"repo": "ruff", "hooks": ["check"]}]}
    target = {"repos": [{"repo": "black"}, {"repo": "ruff", "hooks": ["fmt", "check"]}]}

    assert not check_fragment(target, fragment)


def test_non_string_keys_match_at_every_depth():
    fragment = {200: "ok", "codes": {404: "missing"}}
    target = {200: "ok", "codes": {404: "missing", 500: "error"}}

    assert not check_fragment(target, fragment)
    assert check_fragment({"codes": {}}, fragment) == (unmet("200: missing"),)
    assert check_fragment({200: "ok", "codes": {}}, fragment) == (
        unmet("codes.404: missing"),
    )


def test_unreadable_target_fails():
    assert check_fragment(RepoError("not valid toml: bad")) == (
        "ci.github: `pyproject.toml` unreadable: not valid toml: bad",
    )


def test_missing_target_fails():
    assert check_fragment(None) == ("ci.github: `pyproject.toml` missing",)


def test_fragment_is_checked_under_each_root():
    bit = FragmentBit(
        path=PurePosixPath("pyproject.toml"), fragment="ruff.toml", content=FRAGMENT
    )

    assert check([FRAGMENT, {"tool": {}}], "a", "b", bit=bit) == (
        "ci.github: `b/pyproject.toml` lacks `ruff.toml`: tool.ruff: missing",
    )
