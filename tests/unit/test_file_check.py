from pathlib import PurePosixPath
from unittest.mock import MagicMock, call

import pytest

from exemplar.mills import FileCheckService
from exemplar.pacts import FileBit, Pick, RepoError

BIT = FileBit(path=PurePosixPath(".github/renovate.json"), content="{}\n")


def check(texts, *roots):
    repo = MagicMock()
    repo.read.side_effect = texts
    pick = Pick(
        category="ci",
        variant="github",
        roots=tuple(PurePosixPath(root) for root in roots or (".",)),
    )
    problems = FileCheckService(repo).check(pick, BIT)
    assert repo.read.call_args_list == [
        call(PurePosixPath(root) / BIT.path) for root in roots or (".",)
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
