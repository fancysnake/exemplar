"""Business invariants: constants only mills read."""

from pathlib import PurePosixPath

EXEMPLAR_TOML = PurePosixPath("exemplar.toml")
# What an optional category picks when the repository has nothing for it.
NONE = "none"
