from pathlib import PurePosixPath
from unittest.mock import MagicMock

import pytest

from exemplar.mills import PicksService
from exemplar.pacts import Category, Pick, Picks, Problem, RepoError, Variant

STANDARDS = {
    "docs": Category(
        optional=True, shared=(), variants={"mkdocs-mise": Variant(bits=())}
    ),
    "framework": Category(
        optional=False, shared=(), variants={"react": Variant(bits=())}
    ),
    "lang": Category(
        optional=False,
        shared=(),
        variants={"node": Variant(bits=()), "python": Variant(bits=())},
    ),
    "lint": Category(
        optional=False,
        shared=(),
        variants={"biome": Variant(bits=()), "ruff": Variant(bits=())},
    ),
}

ALL_PICKED = """\
docs = "none"
framework = "react"
lint = "ruff"
lang = "python"
"""


def read(text):
    repo = MagicMock()
    repo.read.return_value = text
    picks = PicksService(repo).read(STANDARDS)
    repo.read.assert_called_once_with(PurePosixPath("exemplar.toml"))
    return picks


def pick(category, variant, *roots):
    return Pick(
        category=category,
        variant=variant,
        roots=tuple(PurePosixPath(root) for root in roots or (".",)),
    )


def test_every_form_normalises_to_variant_and_roots():
    picks = read("""\
docs = "mkdocs-mise"
lint = ["ruff", "biome"]

[lang.node]
root = "frontend"

[lang.python]

[framework.react]
root = ["frontend", "./admin"]
""")

    assert picks == Picks(
        picks=(
            pick("docs", "mkdocs-mise"),
            pick("lint", "ruff"),
            pick("lint", "biome"),
            pick("lang", "node", "frontend"),
            pick("lang", "python"),
            pick("framework", "react", "frontend", "admin"),
        ),
        problems=(),
    )


def test_none_in_optional_category_picks_nothing():
    picks = read(ALL_PICKED)

    assert picks == Picks(
        picks=(
            pick("framework", "react"),
            pick("lint", "ruff"),
            pick("lang", "python"),
        ),
        problems=(),
    )


def test_missing_exemplar_toml_fails():
    assert read(None) == Picks(
        picks=(), problems=(Problem(where="", message="missing"),)
    )


def test_non_utf8_exemplar_toml_fails():
    repo = MagicMock()
    repo.read.side_effect = RepoError("not UTF-8 text")

    picks = PicksService(repo).read(STANDARDS)

    assert picks == Picks(
        picks=(), problems=(Problem(where="", message="unreadable: not UTF-8 text"),)
    )


@pytest.mark.parametrize(
    "text",
    ["docs = \n", "docs = 1\n", "[lang.node]\nroots = 'x'\n", "[lang]\nnode = 'x'\n"],
    ids=["invalid-toml", "wrong-type", "unknown-key", "table-not-of-tables"],
)
def test_malformed_exemplar_toml_fails(text):
    picks = read(text)

    assert not picks.picks
    assert len(picks.problems) == 1
    assert not picks.problems[0].where


@pytest.mark.parametrize(
    "lint", ["lint = []", "[lint]"], ids=["empty-list", "empty-table"]
)
def test_category_not_picked_fails(lint):
    picks = read(f'docs = "none"\nframework = "react"\nlang = "python"\n{lint}\n')

    assert picks.problems == (Problem(where="lint", message="not picked"),)


def test_every_unpicked_category_fails():
    assert read("").problems == (
        Problem(where="docs", message="not picked"),
        Problem(where="framework", message="not picked"),
        Problem(where="lang", message="not picked"),
        Problem(where="lint", message="not picked"),
    )


@pytest.mark.parametrize(
    ("line", "problem"),
    [
        ('ci = "github"', Problem(where="ci", message="unknown category")),
        (
            'lint = ["ruff", "eslint"]',
            Problem(where="lint", message="unknown variant `eslint`"),
        ),
        (
            'lint = "_shared"',
            Problem(where="lint", message="unknown variant `_shared`"),
        ),
        (
            'lint = "none"',
            Problem(where="lint", message="required, cannot pick `none`"),
        ),
        (
            'docs = ["none", "mkdocs-mise"]',
            Problem(where="docs", message="`none` mixed with other picks"),
        ),
        (
            "docs = { none = { root = '/srv' } }",
            Problem(where="docs", message="`none` cannot be a table"),
        ),
        (
            "lang = { node = { root = [] } }",
            Problem(where="lang.node", message="no root"),
        ),
        (
            "lang = { node = { root = '/srv' } }",
            Problem(
                where="lang.node", message="root `/srv` is not inside the repository"
            ),
        ),
        (
            "lang = { node = { root = ['frontend', 'a/../..'] } }",
            Problem(
                where="lang.node", message="root `a/../..` is not inside the repository"
            ),
        ),
        (
            'lint = ["ruff", "biome", "ruff"]',
            Problem(where="lint", message="`ruff` picked twice"),
        ),
        (
            'docs = ["none", "none"]',
            Problem(where="docs", message="`none` picked twice"),
        ),
        (
            "lang = { node = { root = ['frontend', './frontend'] } }",
            Problem(where="lang.node", message="root `./frontend` listed twice"),
        ),
    ],
)
def test_bad_pick_fails(line, problem):
    category = line.split()[0]
    others = [row for row in ALL_PICKED.splitlines() if row.split()[0] != category]

    picks = read("\n".join([*others, line]))

    assert picks.problems == (problem,)


def test_repeated_variant_keeps_first_pick():
    picks = read(ALL_PICKED.replace('lint = "ruff"', 'lint = ["ruff", "ruff"]'))

    assert pick("lint", "ruff") in picks.picks
    assert len(picks.picks) == len(set(picks.picks))


def test_problems_are_all_collected():
    picks = read('docs = "nope"\nlint = "none"\nci = "github"\n')

    assert picks == Picks(
        picks=(),
        problems=(
            Problem(where="docs", message="unknown variant `nope`"),
            Problem(where="lint", message="required, cannot pick `none`"),
            Problem(where="ci", message="unknown category"),
            Problem(where="framework", message="not picked"),
            Problem(where="lang", message="not picked"),
        ),
    )
