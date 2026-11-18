from pathlib import PurePosixPath
from unittest.mock import MagicMock, call

import pytest

from exemplar.mills import BitCheckService
from exemplar.pacts import FileBit, FragmentBit, RepoError

BIT = FileBit(path=PurePosixPath(".github/renovate.json"), content="{}\n")


# The problem under each root; `None` where the bit passed.
def check(contents, *roots, bit=BIT):
    repo = MagicMock()
    read = repo.read if isinstance(bit, FileBit) else repo.read_table
    read.side_effect = contents
    paths = tuple(PurePosixPath(root) for root in roots or (".",))
    service = BitCheckService(repo)
    problems = tuple(service.check(path, bit) for path in paths)
    assert read.call_args_list == [call(path / bit.path) for path in paths]
    return problems


def test_identical_file_passes():
    assert check(["{}\n"]) == (None,)


@pytest.mark.parametrize(
    ("text", "problem"),
    [
        (None, "missing"),
        ("{ }\n", "differs from the standard"),
        ("{}\r\n", "differs from the standard"),
        ("{}", "differs from the standard"),
    ],
    ids=["missing", "different", "line-endings", "no-final-newline"],
)
def test_file_not_matching_fails(text, problem):
    assert check([text]) == (problem,)


def test_unreadable_file_fails():
    assert check([RepoError("not UTF-8 text")]) == ("unreadable: not UTF-8 text",)


def test_bit_is_read_under_its_root():
    assert check([None, "{}\n", "{ }\n"], "frontend", "admin", "api") == (
        "missing",
        None,
        "differs from the standard",
    )


FRAGMENT = {"tool": {"ruff": {"line-length": 88, "select": ["E", "F"]}}}


def check_fragment(target, fragment=None):
    bit = FragmentBit(
        path=PurePosixPath("pyproject.toml"),
        fragment="ruff.toml",
        content=fragment or FRAGMENT,
    )
    (problem,) = check([target], bit=bit)
    return problem


def test_equal_fragment_passes():
    assert check_fragment(FRAGMENT) is None


def test_extra_keys_and_items_pass():
    target = {
        "project": {"name": "x"},
        "tool": {"ruff": {"line-length": 88, "select": ["I", "F", "E"], "fix": True}},
    }

    assert check_fragment(target) is None


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
    assert check_fragment({"tool": {"ruff": ruff}}) == mismatch


def test_table_replaced_by_value_fails():
    assert check_fragment({"tool": {"ruff": 1}}) == "tool.ruff: expected a table, got 1"


def test_array_items_match_as_fragments():
    fragment = {"repos": [{"repo": "ruff", "hooks": ["check"]}]}
    target = {"repos": [{"repo": "black"}, {"repo": "ruff", "hooks": ["fmt", "check"]}]}

    assert check_fragment(target, fragment) is None


@pytest.mark.parametrize(
    "target",
    [
        {"dependency-groups": {"docs": ["mkdocs-material (>=9.6,<10.0)"]}},
        {"dependency-groups": {"docs": ["Mkdocs_Material[imaging]>=9"]}},
        {"project": {"dependencies": ["mkdocs.material"]}},
        {"project": {"optional-dependencies": {"docs": ["mkdocs-material==9.6"]}}},
    ],
    ids=["constraint", "spelling-and-extras", "dependencies", "optional"],
)
def test_requirements_match_by_package_name(target):
    (table,) = target
    fragment = {table: _requirements(target[table], ["mkdocs-material"])}

    assert check_fragment(target, fragment) is None


def _requirements(shape, requirements):
    if isinstance(shape, list):
        return requirements
    return {name: _requirements(value, requirements) for name, value in shape.items()}


def test_requirement_of_another_package_fails():
    fragment = {"dependency-groups": {"docs": ["mkdocs-material (>=9.6,<10.0)"]}}
    target = {"dependency-groups": {"docs": [{"include-group": "dev"}, "mkdocs>=1"]}}

    assert check_fragment(target, fragment) == (
        'dependency-groups.docs: missing "mkdocs-material"'
    )


def test_strings_outside_requirement_arrays_match_exactly():
    fragment = {"tool": {"dependencies": ["mkdocs-material"]}}
    target = {"tool": {"dependencies": ["mkdocs-material>=9"]}}

    assert check_fragment(target, fragment) == (
        'tool.dependencies: missing "mkdocs-material"'
    )


def test_non_string_keys_match_at_every_depth():
    fragment = {200: "ok", "codes": {404: "missing"}}
    target = {200: "ok", "codes": {404: "missing", 500: "error"}}

    assert check_fragment(target, fragment) is None
    assert check_fragment({"codes": {}}, fragment) == "200: missing"
    assert check_fragment({200: "ok", "codes": {}}, fragment) == "codes.404: missing"


def test_unreadable_target_fails():
    assert check_fragment(RepoError("not valid toml: bad")) == (
        "unreadable: not valid toml: bad"
    )


def test_missing_target_fails():
    assert check_fragment(None) == "missing"


def test_fragment_is_checked_under_each_root():
    bit = FragmentBit(
        path=PurePosixPath("pyproject.toml"), fragment="ruff.toml", content=FRAGMENT
    )

    assert check([FRAGMENT, {"tool": {}}], "a", "b", bit=bit) == (
        None,
        "tool.ruff: missing",
    )
