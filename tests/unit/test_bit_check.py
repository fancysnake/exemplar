from pathlib import PurePosixPath
from unittest.mock import MagicMock, call

import msgspec
import pytest

from exemplar.mills import BitCheckService
from exemplar.pacts import FileBit, FragmentBit, Pick, RepoError, StandardsError

BIT = FileBit(path=PurePosixPath(".github/renovate.json"), content="{}\n")


def check(texts, *roots, bit=BIT):
    repo = MagicMock()
    repo.read.side_effect = texts
    pick = Pick(
        category="ci",
        variant="github",
        roots=tuple(PurePosixPath(root) for root in roots or (".",)),
    )
    problems = BitCheckService(repo).check(pick, bit)
    assert repo.read.call_args_list == [
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


# One fragment written in each format, and targets for it as data, so each
# case runs against TOML, YAML and JSON alike.
FRAGMENT = {"tool": {"ruff": {"line-length": 88, "select": ["E", "F"]}}}


def dump(data, format_):
    return getattr(msgspec, format_).encode(data).decode()


def fragment_bit(format_, data):
    return FragmentBit(
        path=PurePosixPath(f"pyproject.{format_}"),
        fragment=f"ruff.{format_}",
        format=format_,
        content=dump(data, format_),
    )


def check_fragment(format_, target, fragment=None):
    text = target if isinstance(target, str | None) else dump(target, format_)
    return check([text], bit=fragment_bit(format_, fragment or FRAGMENT))


def unmet(format_, mismatch):
    return f"ci.github: `pyproject.{format_}` ⊇ `ruff.{format_}`: {mismatch}"


FORMATS = pytest.mark.parametrize("format_", ["toml", "yaml", "json"])


@FORMATS
def test_equal_fragment_passes(format_):
    assert not check_fragment(format_, FRAGMENT)


@FORMATS
def test_extra_keys_and_items_pass(format_):
    target = {
        "project": {"name": "x"},
        "tool": {"ruff": {"line-length": 88, "select": ["I", "F", "E"], "fix": True}},
    }

    assert not check_fragment(format_, target)


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
@FORMATS
def test_first_mismatch_fails(format_, ruff, mismatch):
    assert check_fragment(format_, {"tool": {"ruff": ruff}}) == (
        unmet(format_, mismatch),
    )


@FORMATS
def test_table_replaced_by_value_fails(format_):
    assert check_fragment(format_, {"tool": {"ruff": 1}}) == (
        unmet(format_, "tool.ruff: expected a table, got 1"),
    )


@FORMATS
def test_array_items_match_as_fragments(format_):
    fragment = {"repos": [{"repo": "ruff", "hooks": ["check"]}]}
    target = {"repos": [{"repo": "black"}, {"repo": "ruff", "hooks": ["fmt", "check"]}]}

    assert not check_fragment(format_, target, fragment)


@FORMATS
def test_unparseable_target_fails(format_):
    (problem,) = check_fragment(format_, "[")

    assert problem.startswith(f"ci.github: `pyproject.{format_}` not valid {format_}: ")


@FORMATS
def test_missing_target_fails(format_):
    assert check_fragment(format_, None) == (
        f"ci.github: `pyproject.{format_}` missing",
    )


def test_fragment_is_checked_under_each_root():
    bit = fragment_bit("toml", FRAGMENT)

    assert check([dump(FRAGMENT, "toml"), "[tool]\n"], "a", "b", bit=bit) == (
        "ci.github: `b/pyproject.toml` ⊇ `ruff.toml`: tool.ruff: missing",
    )


def test_unparseable_fragment_is_a_standards_error():
    bit = FragmentBit(
        path=PurePosixPath("pyproject.toml"),
        fragment="ruff.toml",
        format="toml",
        content="[",
    )
    pick = Pick(category="lint", variant="ruff", roots=(PurePosixPath(),))

    with pytest.raises(StandardsError, match=r"^`ruff.toml`: not valid toml: "):
        BitCheckService(MagicMock()).check(pick, bit)
