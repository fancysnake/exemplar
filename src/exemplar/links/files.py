"""Reading a file on disk as text, for every link that reads one."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


# `None` when nothing is at the path; `error(reason)` when something is, but it
# cannot be read as UTF-8 text. The caller decides how the reason names the file.
def read_text(file: Path, error: Callable[[str], Exception]) -> str | None:
    try:
        return file.read_text(encoding="utf-8", newline="")
    # A parent that is a file means the path does not exist either.
    except FileNotFoundError, NotADirectoryError:
        return None
    except OSError as cause:
        raise error(cause.strerror or str(cause)) from cause
    except UnicodeDecodeError as cause:
        reason = "not UTF-8 text"
        raise error(reason) from cause
