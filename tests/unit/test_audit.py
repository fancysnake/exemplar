from pathlib import PurePosixPath
from unittest.mock import MagicMock, call

from exemplar.mills import AuditService
from exemplar.pacts import Category, FileBit, Pick, Picks, Problem, Report, Variant

SHARED = FileBit(path=PurePosixPath("LICENSE"), content="MIT\n")
RUFF = FileBit(path=PurePosixPath("ruff.toml"), content="")
STANDARDS = {
    "lint": Category(
        optional=False,
        shared=(SHARED,),
        variants={"ruff": Variant(bits=(RUFF,)), "biome": Variant(bits=())},
    )
}
PICK = Pick(category="lint", variant="ruff", roots=(PurePosixPath(),))
PROBLEM = Problem(category="lint", message="`biome` picked twice")


def test_checks_variant_then_shared_bits_of_each_pick():
    standards, picks, bits = MagicMock(), MagicMock(), MagicMock()
    standards.read.return_value = STANDARDS
    picks.read.return_value = Picks(picks=(PICK,), problems=(PROBLEM,))
    bits.check.side_effect = [("ruff",), ("license",)]

    report = AuditService(standards, picks, bits).audit()

    picks.read.assert_called_once_with(STANDARDS)
    assert bits.check.call_args_list == [call(PICK, RUFF), call(PICK, SHARED)]
    assert report == Report(problems=(PROBLEM,), results=("ruff", "license"))


def test_no_picks_checks_no_bits():
    standards, picks, bits = MagicMock(), MagicMock(), MagicMock()
    standards.read.return_value = STANDARDS
    picks.read.return_value = Picks(picks=(), problems=(PROBLEM,))

    report = AuditService(standards, picks, bits).audit()

    bits.check.assert_not_called()
    assert report == Report(problems=(PROBLEM,), results=())
