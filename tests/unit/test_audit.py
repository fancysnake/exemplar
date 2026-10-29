from pathlib import PurePosixPath
from unittest.mock import MagicMock, call

from exemplar.mills import AuditService
from exemplar.pacts import (
    Category,
    FileBit,
    Pick,
    Picks,
    PicksSection,
    Problem,
    Report,
    Result,
    Section,
    Variant,
)

SHARED = FileBit(path=PurePosixPath("LICENSE"), content="MIT\n")
RUFF = FileBit(path=PurePosixPath("ruff.toml"), content="")
STANDARDS = {
    "lint": Category(
        optional=False,
        shared=(SHARED,),
        variants={"ruff": Variant(bits=(RUFF,)), "biome": Variant(bits=())},
    )
}
API, WEB = PurePosixPath("api"), PurePosixPath("web")
PICK = Pick(category="lint", variant="ruff", roots=(API, WEB))
PROBLEM = Problem(where="lint", message="`biome` picked twice")
PICKS = PicksSection(path=PurePosixPath("exemplar.toml"), problems=(PROBLEM,))


def audit(picks, *problems):
    standards, picks_service, bits = MagicMock(), MagicMock(), MagicMock()
    standards.read.return_value = STANDARDS
    picks_service.read.return_value = picks
    bits.check.side_effect = problems
    report = AuditService(standards, picks_service, bits).audit()
    picks_service.read.assert_called_once_with(STANDARDS)
    return report, bits


def test_sections_per_root_check_variant_then_shared_bits():
    report, bits = audit(
        Picks(picks=(PICK,), problems=(PROBLEM,)), "missing", None, None, None
    )

    assert bits.check.call_args_list == [
        call(API, RUFF),
        call(API, SHARED),
        call(WEB, RUFF),
        call(WEB, SHARED),
    ]
    assert report == Report(
        picks=PICKS,
        sections=(
            Section(
                category="lint",
                variant="ruff",
                root=API,
                results=(
                    Result(bit=RUFF, problem="missing"),
                    Result(bit=SHARED, problem=None),
                ),
            ),
            Section(
                category="lint",
                variant="ruff",
                root=WEB,
                results=(
                    Result(bit=RUFF, problem=None),
                    Result(bit=SHARED, problem=None),
                ),
            ),
        ),
    )


def test_no_picks_checks_no_bits():
    report, bits = audit(Picks(picks=(), problems=(PROBLEM,)))

    bits.check.assert_not_called()
    assert report == Report(picks=PICKS, sections=())


def section(*problems):
    return Section(
        category="lint",
        variant="ruff",
        root=API,
        results=tuple(Result(bit=RUFF, problem=problem) for problem in problems),
    )


def test_report_is_open_while_any_item_is():
    empty = PicksSection(path=PurePosixPath("exemplar.toml"), problems=())

    assert not Report(picks=empty, sections=(section(None, None),)).open
    assert Report(picks=empty, sections=(section(None, "missing"),)).open
    assert Report(picks=PICKS, sections=(section(None),)).open
