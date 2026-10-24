from pathlib import PurePosixPath
from unittest.mock import MagicMock

import pytest

from exemplar.mills import PicksService
from exemplar.pacts import Category, Pick, Picks, Variant

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
    assert read(None) == Picks(picks=(), problems=("exemplar.toml: missing",))


@pytest.mark.parametrize(
    "text",
    ["docs = \n", "docs = 1\n", "[lang.node]\nroots = 'x'\n", "[lang]\nnode = 'x'\n"],
    ids=["invalid-toml", "wrong-type", "unknown-key", "table-not-of-tables"],
)
def test_malformed_exemplar_toml_fails(text):
    picks = read(text)

    assert not picks.picks
    assert len(picks.problems) == 1
    assert picks.problems[0].startswith("exemplar.toml: ")


@pytest.mark.parametrize(
    "lint", ["lint = []", "[lint]"], ids=["empty-list", "empty-table"]
)
def test_category_not_picked_fails(lint):
    picks = read(f'docs = "none"\nframework = "react"\nlang = "python"\n{lint}\n')

    assert picks.problems == ("lint: not picked",)


def test_every_unpicked_category_fails():
    assert read("").problems == (
        "docs: not picked",
        "framework: not picked",
        "lang: not picked",
        "lint: not picked",
    )


@pytest.mark.parametrize(
    ("line", "problem"),
    [
        ('ci = "github"', "ci: unknown category"),
        ('lint = ["ruff", "eslint"]', "lint: unknown variant `eslint`"),
        ('lint = "_shared"', "lint: unknown variant `_shared`"),
        ('lint = "none"', "lint: required, cannot pick `none`"),
        ('docs = ["none", "mkdocs-mise"]', "docs: `none` mixed with other picks"),
        ("lang = { node = { root = [] } }", "lang.node: no root"),
        (
            "lang = { node = { root = '/srv' } }",
            "lang.node: root `/srv` is not inside the repository",
        ),
        (
            "lang = { node = { root = ['frontend', 'a/../..'] } }",
            "lang.node: root `a/../..` is not inside the repository",
        ),
        ('lint = ["ruff", "biome", "ruff"]', "lint: `ruff` picked twice"),
        ('docs = ["none", "none"]', "docs: `none` picked twice"),
        (
            "lang = { node = { root = ['frontend', './frontend'] } }",
            "lang.node: root `./frontend` listed twice",
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
            "docs: unknown variant `nope`",
            "lint: required, cannot pick `none`",
            "ci: unknown category",
            "framework: not picked",
            "lang: not picked",
        ),
    )
